import { useEffect, useRef } from "react";
import type { Message } from "../types/chat";
import { MessageBubble } from "./MessageBubble";

export function ChatWindow({
  messages,
  conversationId,
  onSuggestedQuestion,
}: {
  messages: Message[];
  conversationId: string;
  onSuggestedQuestion: (q: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "16px 0",
        background: "#F5F5F5",
      }}
    >
      {messages.length === 0 && (
        <div
          style={{
            textAlign: "center",
            color: "#888",
            marginTop: 60,
            fontSize: 14,
          }}
        >
          <p style={{ fontSize: 32 }}>🏢</p>
          <p>Ask me anything about HR policies.</p>
        </div>
      )}
      {messages.map((m) => (
        <MessageBubble
          key={m.id}
          message={m}
          conversationId={conversationId}
          onSuggestedQuestion={onSuggestedQuestion}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
