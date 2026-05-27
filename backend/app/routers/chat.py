import uuid
import json
import logging
import traceback
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
from openai import BadRequestError
from app.models.schemas import ChatRequest
from app.services.embeddings import embed_query
from app.services.retrieval import retrieve_chunks
from app.services.parent_fetch import assemble_context, limit_citations
from app.services.llm import stream_answer
from app.services.session import get_history, append_turn
from app.services.speech import transcribe_audio, synthesize_speech

router = APIRouter()
FOLLOW_UP_PREFIXES = (
    "it", "its", "they", "them", "their", "this", "that", "these", "those",
    "he", "she", "there", "here",
)
MAX_SUGGESTED_QUESTIONS = 3


def get_user_facing_error_message(exc: Exception) -> str:
    """Map backend errors to concise messages safe for the chat UI."""
    if isinstance(exc, BadRequestError):
        error_text = str(exc).lower()
        if "content_filter" in error_text or "content management policy" in error_text:
            return "I couldn't answer that because the request was blocked by Azure OpenAI safety filters. Please rephrase and try again."
        return "The request could not be processed. Please rephrase and try again."

    error_text = str(exc).lower()
    if "timeout" in error_text:
        return "The request timed out while contacting a backend service. Please try again."

    return "Something went wrong while processing the request. Please try again."


def rewrite_stale_refusal(answer_text: str, query_text: str, history: list[dict]) -> str:
    """Replace the generic refusal with a context-aware response when possible."""
    normalized_answer = answer_text.strip()
    refusal_variants = {
        "I can only answer HR policy questions.",
        "I can help with HR policy questions. Please ask about a policy, benefit, leave rule, attendance rule, or similar HR topic.",
    }
    if normalized_answer not in refusal_variants:
        return answer_text

    previous_user = next(
        (msg["content"] for msg in reversed(history) if msg.get("role") == "user"),
        None,
    )
    if previous_user:
        topic = previous_user.strip().rstrip("?.!")
        return f"I understand. Based on your previous HR policy question about \"{topic}\", what detail would you like me to clarify?"

    return "I understand. Please tell me what HR policy detail you want to know, and I will answer from the policy documents."


def build_retrieval_query(query_text: str, history: list[dict]) -> str:
    """Expand follow-up questions with the previous user turn for retrieval."""
    prior_user_messages = [msg["content"] for msg in history if msg.get("role") == "user"]
    if not prior_user_messages:
        return query_text

    normalized = query_text.strip().lower()
    is_follow_up = (
        len(normalized.split()) <= 12
        or normalized.startswith(FOLLOW_UP_PREFIXES)
        or " it " in f" {normalized} "
        or " they " in f" {normalized} "
    )
    if not is_follow_up:
        return query_text

    return f"{prior_user_messages[-1]}\nFollow-up question: {query_text}"


async def filter_suggested_questions(
    questions: list[str],
    allowed_chunks: list[dict],
) -> list[str]:
    """Keep only follow-up questions that retrieve back to the same policy context."""
    if not questions:
        return []

    allowed_section_ids = {
        chunk.get("section_id")
        for chunk in allowed_chunks
        if chunk.get("section_id")
    }
    allowed_document_ids = {
        chunk.get("document_id")
        for chunk in allowed_chunks
        if chunk.get("document_id")
    }

    filtered: list[str] = []
    seen_questions: set[str] = set()

    for question in questions:
        normalized = question.strip()
        if not normalized:
            continue

        dedupe_key = normalized.casefold()
        if dedupe_key in seen_questions:
            continue

        seen_questions.add(dedupe_key)
        query_vector = await embed_query(normalized)
        candidate_chunks = await retrieve_chunks(normalized, query_vector, top_k=3)
        if not candidate_chunks:
            continue

        matches_context = any(
            (
                chunk.get("section_id") in allowed_section_ids
                or chunk.get("document_id") in allowed_document_ids
            )
            for chunk in candidate_chunks
        )
        if not matches_context:
            continue

        filtered.append(normalized)
        if len(filtered) >= MAX_SUGGESTED_QUESTIONS:
            break

    return filtered


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

            # 1. Get session history and build a retrieval-friendly query
            history = await get_history(request.conversation_id)
            retrieval_query = build_retrieval_query(query_text, history)

            # 2. Embed query
            query_vector = await embed_query(retrieval_query)

            # 3. Retrieve child chunks
            chunks = await retrieve_chunks(retrieval_query, query_vector)

            # 4. Fetch parent sections + build citations
            if not chunks:
                yield f"data: No relevant HR policy information found.\n\n"
                yield f"event: metadata\ndata: {json.dumps({'citations': [], 'suggested_questions': [], 'turn_id': turn_id})}\n\n"
                return

            parent_sections, citations = assemble_context(chunks)
            citations = limit_citations(citations)

            if not parent_sections:
                yield "data: Content temporarily unavailable. Please try again.\n\n"
                yield f"event: metadata\ndata: {json.dumps({'citations': [], 'suggested_questions': [], 'turn_id': turn_id})}\n\n"
                return

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

            full_answer = rewrite_stale_refusal(full_answer, query_text, history)
            suggested_questions = await filter_suggested_questions(suggested_questions, chunks)

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
            yield f"event: error\ndata: {json.dumps({'message': get_user_facing_error_message(e)})}\n\n"

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
