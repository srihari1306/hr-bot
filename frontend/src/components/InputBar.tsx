import { useState } from "react";
import type { KeyboardEvent } from "react";
import { VoiceButton } from "./VoiceButton";
import type { VoiceState } from "../hooks/useVoice";

export function InputBar({
  onSend,
  disabled,
  voiceState,
  onVoiceStart,
  onVoiceStop,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
  voiceState: VoiceState;
  onVoiceStart: () => void;
  onVoiceStop: () => void;
}) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (value.trim() && !disabled) {
      onSend(value.trim());
      setValue("");
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        padding: "12px 16px",
        borderTop: "1px solid #E0E0E0",
        background: "#FAFAFA",
      }}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Ask an HR policy question..."
        disabled={disabled}
        rows={1}
        style={{
          flex: 1,
          resize: "none",
          border: "1px solid #D1D1D1",
          borderRadius: 8,
          padding: "8px 12px",
          fontSize: 14,
          fontFamily: "inherit",
          outline: "none",
          background: disabled ? "#F5F5F5" : "#FFF",
        }}
      />
      <VoiceButton
        voiceState={voiceState}
        onStart={onVoiceStart}
        onStop={onVoiceStop}
        disabled={disabled && voiceState === "idle"}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        style={{
          background: "#6264A7",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          padding: "0 18px",
          cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
          fontSize: 20,
          opacity: disabled || !value.trim() ? 0.5 : 1,
        }}
      >
        ➤
      </button>
    </div>
  );
}
