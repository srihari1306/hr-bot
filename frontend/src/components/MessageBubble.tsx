import type { Message } from "../types/chat";
import { CitationChip } from "./CitationChip";
import { FeedbackRow } from "./FeedbackRow";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { TypingIndicator } from "./TypingIndicator";

export function MessageBubble({
  message,
  conversationId,
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
            <div style={{ whiteSpace: "pre-wrap" }}>{message.content}</div>

            {/* Citations */}
            {message.citations && message.citations.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {message.citations.map((c, i) => (
                  <CitationChip key={i} citation={c} />
                ))}
              </div>
            )}

            {/* Feedback */}
            {!isUser && !message.streaming && message.turnId && (
              <FeedbackRow
                conversationId={conversationId}
                turnId={message.turnId}
              />
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
