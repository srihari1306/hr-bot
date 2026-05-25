export function SuggestedQuestions({
  questions,
  onSelect,
}: {
  questions: string[];
  onSelect: (q: string) => void;
}) {
  if (!questions.length) return null;
  return (
    <div style={{ marginTop: 10 }}>
      <p style={{ fontSize: 11, color: "#888", margin: "0 0 4px" }}>
        You might also ask:
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            style={{
              background: "#F5F5F5",
              border: "1px solid #E0E0E0",
              borderRadius: 8,
              padding: "5px 10px",
              cursor: "pointer",
              textAlign: "left",
              fontSize: 12,
              color: "#333",
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
