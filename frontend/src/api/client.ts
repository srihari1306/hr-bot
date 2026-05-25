const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function postChatStream(
  message: string,
  conversationId: string,
  onToken: (token: string) => void,
  onMetadata: (metadata: { citations: any[]; suggested_questions: string[]; turn_id: string }) => void,
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
            if (currentEvent === "metadata") {
              onMetadata(parsed);
            } else if (currentEvent === "error") {
              onError(parsed.message || "Unknown error");
            } else if (parsed.token) {
              onToken(parsed.token);
            }
          } catch {
            // ignore unparseable lines
          }
          currentEvent = "";
        }
      }
    }
  } catch (err) {
    onError(err instanceof Error ? err.message : "Connection failed");
  }
}

export async function postFeedback(
  conversationId: string,
  turnId: string,
  rating: "up" | "down"
) {
  await fetch(`${BASE_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: conversationId,
      turn_id: turnId,
      rating,
    }),
  });
}
