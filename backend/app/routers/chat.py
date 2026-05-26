import uuid
import json
import logging
import traceback
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
from app.models.schemas import ChatRequest
from app.services.embeddings import embed_query
from app.services.retrieval import retrieve_chunks
from app.services.parent_fetch import assemble_context
from app.services.llm import stream_answer
from app.services.session import get_history, append_turn
from app.services.speech import transcribe_audio, synthesize_speech

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    """SSE streaming chat endpoint. Streams tokens, then sends metadata event."""
    async def event_generator():
        turn_id = str(uuid.uuid4())[:8]
        full_answer = ""

        try:
            # --- Handle voice input ---
            query_text = request.message

            if request.voice_input:
                try:
                    transcript, confidence = transcribe_audio(request.message)
                    if confidence < 0.75 or not transcript:
                        yield f"event: reprompt\ndata: {json.dumps({'message': 'Could not understand audio. Please try again.'})}\n\n"
                        return
                    query_text = transcript
                    # Send transcript back so UI can display what was heard
                    yield f"event: transcript\ndata: {json.dumps({'text': query_text})}\n\n"
                except Exception as e:
                    logging.error("STT error: %s\n%s", str(e), traceback.format_exc())
                    yield f"event: error\ndata: {json.dumps({'message': f'STT error: {str(e)}'})}\n\n"
                    return

            # 1. Embed query
            query_vector = await embed_query(query_text)

            # 2. Retrieve child chunks
            chunks = await retrieve_chunks(query_text, query_vector)

            # 3. Fetch parent sections + build citations
            if not chunks:
                yield f"data: No relevant HR policy information found.\n\n"
                yield f"event: metadata\ndata: {json.dumps({'citations': [], 'suggested_questions': [], 'turn_id': turn_id})}\n\n"
                return

            parent_sections, citations = assemble_context(chunks)

            if not parent_sections:
                yield "data: Content temporarily unavailable. Please try again.\n\n"
                yield f"event: metadata\ndata: {json.dumps({'citations': [], 'suggested_questions': [], 'turn_id': turn_id})}\n\n"
                return

            # 4. Get session history
            history = await get_history(request.conversation_id)

            # 5. Stream GPT-4o response
            suggested_questions = []
            json_marker = '{"suggested_questions"'
            output_buffer = ""
            json_detected = False

            stream = stream_answer(query_text, parent_sections, history)
            async for token in stream:
                full_answer += token
                output_buffer += token

                # Check if the JSON block has started
                if json_marker in output_buffer:
                    # Yield only the text before the JSON block
                    pre_json = output_buffer.split(json_marker, 1)[0]
                    if pre_json:
                        yield f"data: {json.dumps({'token': pre_json})}\n\n"
                    json_detected = True
                    break

                # Yield only the "safe" portion that can't be a prefix of json_marker
                safe_end = len(output_buffer) - len(json_marker) + 1
                if safe_end > 0:
                    yield f"data: {json.dumps({'token': output_buffer[:safe_end]})}\n\n"
                    output_buffer = output_buffer[safe_end:]

            # Flush remaining buffer if no JSON was found
            if not json_detected and output_buffer:
                yield f"data: {json.dumps({'token': output_buffer})}\n\n"

            # Consume remaining tokens to complete the JSON
            if json_detected:
                async for token in stream:
                    full_answer += token

            # Extract suggested questions from the full answer
            if json_marker in full_answer:
                answer_text, json_part = full_answer.split(json_marker, 1)
                try:
                    sq_data = json.loads(json_marker + json_part)
                    suggested_questions = sq_data.get("suggested_questions", [])
                    full_answer = answer_text.strip()
                except Exception:
                    pass

            # 6. Save to session
            await append_turn(request.conversation_id, query_text, full_answer)

            # 7. Send final metadata event
            metadata = {
                "citations": citations,
                "suggested_questions": suggested_questions,
                "turn_id": turn_id,
                "answer_text": full_answer       # used by frontend for TTS (avoids stale closure)
            }
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            logging.error("Chat error: %s\n%s", str(e), traceback.format_exc())
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/tts")
async def tts(text: str):
    """Synthesize text to MP3. Called by frontend after streaming completes."""
    try:
        audio_bytes = synthesize_speech(text)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"}
        )
    except Exception as e:
        logging.error("TTS error: %s\n%s", str(e), traceback.format_exc())
        return Response(status_code=500, content=str(e))
