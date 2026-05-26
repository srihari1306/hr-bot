import ReactMarkdown from "react-markdown";
import type { Message } from "../types/chat";
import { CitationChip } from "./CitationChip";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { TypingIndicator } from "./TypingIndicator";

export function MessageBubble({
  message,
  onSuggestedQuestion,
}: {
  message: Message;
  conversationId: string;
  onSuggestedQuestion: (q: string) => void;
}) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 12,
        padding: "0 16px",
      }}
    >
      <div
        style={{
          maxWidth: "75%",
          background: isUser ? "#6264A7" : "#FFFFFF",
          color: isUser ? "#fff" : "#242424",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          padding: "10px 14px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          fontSize: 14,
          lineHeight: 1.5,
        }}
      >
        {message.streaming && !message.content ? (
          <TypingIndicator />
        ) : (
          <>
            <ReactMarkdown
              components={{
                p: ({ children }) => <p style={{ margin: "0 0 8px" }}>{children}</p>,
                ul: ({ children }) => <ul style={{ paddingLeft: 20, margin: "0 0 8px" }}>{children}</ul>,
                ol: ({ children }) => <ol style={{ paddingLeft: 20, margin: "0 0 8px" }}>{children}</ol>,
                li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
                strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                code: ({ children }) => (
                  <code style={{
                    background: isUser ? "rgba(255,255,255,0.15)" : "#F0F0F0",
                    padding: "1px 5px",
                    borderRadius: 4,
                    fontFamily: "monospace",
                    fontSize: 13,
                  }}>{children}</code>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>

            {/* Citations */}
            {message.citations && message.citations.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {message.citations.map((c, i) => (
                  <CitationChip key={i} citation={c} />
                ))}
              </div>
            )}

            {/* Suggested questions */}
            {!isUser && !message.streaming && message.suggestedQuestions && (
              <SuggestedQuestions
                questions={message.suggestedQuestions}
                onSelect={onSuggestedQuestion}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
