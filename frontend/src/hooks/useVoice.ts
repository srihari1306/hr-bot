import { useState, useRef, useCallback } from "react";

export type VoiceState = "idle" | "recording" | "processing" | "playing";

export function useVoice(onTranscript: (base64: string) => void) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });

        // Convert to base64
        const buffer = await blob.arrayBuffer();
        const base64 = btoa(
          new Uint8Array(buffer).reduce((s, b) => s + String.fromCharCode(b), "")
        );

        setVoiceState("processing");
        onTranscript(base64);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setVoiceState("recording");
    } catch {
      setError("Microphone access denied.");
      setVoiceState("idle");
    }
  }, [onTranscript]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
  }, []);

  const playTTS = useCallback(async (text: string, apiBase: string) => {
    setVoiceState("playing");
    try {
      const encoded = encodeURIComponent(text);
      const response = await fetch(`${apiBase}/tts?text=${encoded}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        setVoiceState("idle");
        URL.revokeObjectURL(url);
      };
      audio.play();
    } catch {
      setVoiceState("idle");
    }
  }, []);

  const stopPlayback = useCallback(() => {
    audioRef.current?.pause();
    setVoiceState("idle");
  }, []);

  return {
    voiceState,
    error,
    startRecording,
    stopRecording,
    playTTS,
    stopPlayback,
  };
}
