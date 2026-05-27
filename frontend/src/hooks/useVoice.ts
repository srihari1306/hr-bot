import { useState, useRef, useCallback } from "react";

export type VoiceState = "idle" | "recording" | "processing" | "playing";

export function useVoice(onTranscript: (base64: string) => void) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const resetPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current.onpause = null;
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }

    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }

    setVoiceState("idle");
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    resetPlayback();
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
  }, [onTranscript, resetPlayback]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
  }, []);

  const playTTS = useCallback(async (text: string, apiBase: string) => {
    resetPlayback();
    setVoiceState("playing");
    try {
      const encoded = encodeURIComponent(text);
      const response = await fetch(`${apiBase}/tts?text=${encoded}`);
      if (!response.ok) {
        throw new Error("TTS request failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = resetPlayback;
      audio.onerror = resetPlayback;
      audio.onpause = () => {
        if (audio.ended) {
          return;
        }
        resetPlayback();
      };

      await audio.play();
    } catch {
      resetPlayback();
    }
  }, [resetPlayback]);

  const stopPlayback = useCallback(() => {
    resetPlayback();
  }, [resetPlayback]);

  return {
    voiceState,
    error,
    startRecording,
    stopRecording,
    playTTS,
    stopPlayback,
  };
}
