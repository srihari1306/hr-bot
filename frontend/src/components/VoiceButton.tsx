import type { VoiceState } from "../hooks/useVoice";

export function VoiceButton({
  voiceState,
  onStart,
  onStop,
  disabled,
}: {
  voiceState: VoiceState;
  onStart: () => void;
  onStop: () => void;
  disabled: boolean;
}) {
  const isRecording = voiceState === "recording";
  const isBusy = voiceState === "processing" || voiceState === "playing";

  const handleClick = () => {
    if (isRecording) onStop();
    else if (!isBusy && !disabled) onStart();
  };

  const label = {
    idle: "🎤",
    recording: "⏹️",
    processing: "⏳",
    playing: "🔊",
  }[voiceState];

  return (
    <button
      onClick={handleClick}
      disabled={disabled || isBusy}
      title={isRecording ? "Stop recording" : "Start voice input"}
      style={{
        background: isRecording ? "#C4314B" : "#6264A7",
        color: "#fff",
        border: "none",
        borderRadius: 8,
        padding: "0 14px",
        cursor: disabled || isBusy ? "not-allowed" : "pointer",
        fontSize: 18,
        opacity: disabled || isBusy ? 0.5 : 1,
        animation: isRecording ? "pulse 1s infinite" : "none",
      }}
    >
      {label}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </button>
  );
}
