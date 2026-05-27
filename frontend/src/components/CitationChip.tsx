import type { Citation } from "../types/chat";

export function CitationChip({ citation }: { citation: Citation }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 12,
        background: "#EFF6FC",
        border: "1px solid #CCE4F7",
        color: "#0078D4",
        fontSize: 12,
        marginRight: 6,
        marginTop: 4,
        cursor: "default",
      }}
    >
      📄 {citation.heading}
    </span>
  );
}
