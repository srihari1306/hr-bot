import { useEffect, useState } from "react";
import { app } from "@microsoft/teams-js";
import { ChatWindow } from "./components/ChatWindow";
import { InputBar } from "./components/InputBar";
import { useChat } from "./hooks/useChat";
import "./app.css";

export default function App() {
  const { messages, sendMessage, isStreaming, conversationId, voice } = useChat();
  const [teamsInitialized, setTeamsInitialized] = useState(false);

  useEffect(() => {
    // Try to initialize Teams SDK; fall back gracefully for browser testing
    app.initialize()
      .then(() => setTeamsInitialized(true))
      .catch(() => setTeamsInitialized(true)); // still show the UI outside Teams
  }, []);

  if (!teamsInitialized) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        Loading...
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        fontFamily: "'Segoe UI', sans-serif",
        background: "#fff",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #E0E0E0",
          background: "#6264A7",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span style={{ fontSize: 20 }}>🏢</span>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>HR Policy Assistant</div>
          <div style={{ fontSize: 11, opacity: 0.8 }}>Powered by AI · Ask anything</div>
        </div>
      </div>

      {/* Chat */}
      <ChatWindow
        messages={messages}
        conversationId={conversationId}
        onSuggestedQuestion={sendMessage}
      />

      {/* Input */}
      <InputBar
        onSend={sendMessage}
        disabled={isStreaming}
        voiceState={voice.voiceState}
        onVoiceStart={voice.startRecording}
        onVoiceStop={voice.stopRecording}
      />
    </div>
  );
}
