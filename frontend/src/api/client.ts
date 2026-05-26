const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export { BASE_URL };

// ---------- shared SSE reader ----------

type MetadataPayload = {
  citations: any[];
  suggested_questions: string[];
  turn_id: string;
  answer_text?: string;
};

type SSEHandlers = {
  onToken?: (token: string) => void;
  onMetadata?: (metadata: MetadataPayload) => void;
  onError?: (msg: string) => void;
  onTranscript?: (text: string) => void;
  onReprompt?: (msg: string) => void;
};

async function readSSEStream(response: Response, handlers: SSEHandlers) {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (!data) continue;

        try {
          const parsed = JSON.parse(data);
          if (currentEvent === "metadata") handlers.onMetadata?.(parsed);
          else if (currentEvent === "error") handlers.onError?.(parsed.message || "Unknown error");
          else if (currentEvent === "transcript") handlers.onTranscript?.(parsed.text);
          else if (currentEvent === "reprompt") handlers.onReprompt?.(parsed.message);
          else if (parsed.token) handlers.onToken?.(parsed.token);
        } catch {
          // ignore unparseable lines
        }
        currentEvent = "";
      }
    }
  }
}

// ---------- text chat ----------

export async function postChatStream(
  message: string,
  conversationId: string,
  onToken: (token: string) => void,
  onMetadata: (metadata: MetadataPayload) => void,
  onError: (msg: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        user_id: "local-dev-user",
      }),
    });

    if (!response.ok) {
      onError(`Server error: ${response.status}`);
      return;
    }

    await readSSEStream(response, { onToken, onMetadata, onError });
  } catch (err) {
    onError(err instanceof Error ? err.message : "Connection failed");
  }
}

// ---------- voice chat ----------

export async function postVoiceChatStream(
  audioBase64: string,
  conversationId: string,
  onTranscript: (text: string) => void,
  onToken: (token: string) => void,
  onMetadata: (metadata: MetadataPayload) => void,
  onReprompt: (msg: string) => void,
  onError: (msg: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: audioBase64,
        conversation_id: conversationId,
        user_id: "local-dev-user",
        voice_input: true,
      }),
    });

    if (!response.ok) {
      onError(`Server error: ${response.status}`);
      return;
    }

    await readSSEStream(response, { onToken, onMetadata, onError, onTranscript, onReprompt });
  } catch (err) {
    onError(err instanceof Error ? err.message : "Connection failed");
  }
}

