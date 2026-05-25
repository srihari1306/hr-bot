import { useState } from "react";
import { postFeedback } from "../api/client";

export function FeedbackRow({
  conversationId,
  turnId,
}: {
  conversationId: string;
  turnId: string;
}) {
  const [rated, setRated] = useState<"up" | "down" | null>(null);

  const handleRate = async (rating: "up" | "down") => {
    setRated(rating);
    await postFeedback(conversationId, turnId, rating);
  };

  return (
    <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center" }}>
      <span style={{ fontSize: 11, color: "#888" }}>Was this helpful?</span>
      {(["up", "down"] as const).map((r) => (
        <button
          key={r}
          onClick={() => handleRate(r)}
          disabled={rated !== null}
          style={{
            background: "none",
            border: "none",
            cursor: rated ? "default" : "pointer",
            fontSize: 16,
            opacity: rated && rated !== r ? 0.3 : 1,
          }}
        >
          {r === "up" ? "👍" : "👎"}
        </button>
      ))}
      {rated && (
        <span style={{ fontSize: 11, color: "#888" }}>Thanks!</span>
      )}
    </div>
  );
}
