import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import type { Message } from "../types/chat";
import { postChatStream, postVoiceChatStream, BASE_URL } from "../api/client";
import { useVoice } from "./useVoice";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const conversationId = useRef<string>(uuidv4());
  const lastAnswerRef = useRef<string>("");

  // ---- text chat ----
  const sendMessage = useCallback(async (text: string) => {
    if (isStreaming || !text.trim()) return;

    const userMsg: Message = {
      id: uuidv4(),
      role: "user",
      content: text,
    };

    const assistantMsgId = uuidv4();
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);
    lastAnswerRef.current = "";

    await postChatStream(
      text,
      conversationId.current,
      // onToken
      (token) => {
        lastAnswerRef.current += token;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: m.content + token }
              : m
          )
        );
      },
      // onMetadata
      (meta) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  streaming: false,
                  citations: meta.citations,
                  suggestedQuestions: meta.suggested_questions,
                  turnId: meta.turn_id,
                }
              : m
          )
        );
        setIsStreaming(false);
      },
      // onError
      (errMsg) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: `Error: ${errMsg}`, streaming: false }
              : m
          )
        );
        setIsStreaming(false);
      }
    );
  }, [isStreaming]);

  // ---- voice chat ----
  const sendVoiceMessage = useCallback(async (audioBase64: string) => {
    if (isStreaming) return;

    const assistantMsgId = uuidv4();

    // Placeholder while STT runs
    setMessages((prev) => [...prev, {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      streaming: true,
    }]);
    setIsStreaming(true);
    lastAnswerRef.current = "";

    await postVoiceChatStream(
      audioBase64,
      conversationId.current,
      // onTranscript — show what was heard as user bubble
      (transcript) => {
        setMessages((prev) => [
          ...prev.filter(m => m.id !== assistantMsgId),
          { id: uuidv4(), role: "user", content: `🎤 ${transcript}` },
          { id: assistantMsgId, role: "assistant", content: "", streaming: true },
        ]);
      },
      // onToken
      (token) => {
        lastAnswerRef.current += token;
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsgId
            ? { ...m, content: m.content + token } : m)
        );
      },
      // onMetadata
      (meta) => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsgId
            ? { ...m, streaming: false, citations: meta.citations,
                suggestedQuestions: meta.suggested_questions, turnId: meta.turn_id }
            : m)
        );
        setIsStreaming(false);
        // Auto-play TTS for voice responses
        if (lastAnswerRef.current) {
          voice.playTTS(lastAnswerRef.current, BASE_URL);
        }
      },
      // onReprompt
      (msg) => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsgId
            ? { ...m, content: msg, streaming: false } : m)
        );
        setIsStreaming(false);
      },
      // onError
      (errMsg) => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsgId
            ? { ...m, content: `Error: ${errMsg}`, streaming: false } : m)
        );
        setIsStreaming(false);
      }
    );
  }, [isStreaming]);

  const voice = useVoice((audioBase64) => sendVoiceMessage(audioBase64));

  return {
    messages,
    sendMessage,
    isStreaming,
    conversationId: conversationId.current,
    voice,
  };
}
