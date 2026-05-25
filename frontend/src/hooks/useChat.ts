import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import type { Message } from "../types/chat";
import { postChatStream } from "../api/client";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const conversationId = useRef<string>(uuidv4());

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

    await postChatStream(
      text,
      conversationId.current,
      // onToken
      (token) => {
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

  return { messages, sendMessage, isStreaming, conversationId: conversationId.current };
}
