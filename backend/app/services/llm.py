import os
import uuid
from openai import AsyncAzureOpenAI
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are an HR policy assistant. Answer questions based strictly on the HR policy context provided below.

Rules:
- Only answer questions about HR policies. If a question is unrelated, respond with: "I can only answer HR policy questions."
- Always cite the specific policy section your answer comes from using the format: [Section: <heading>]
- If the answer is not found in the context, say: "I could not find information on this in our HR policies."
- Be concise and accurate. Do not invent policy details.
- After your answer, suggest 2-3 relevant follow-up questions as a JSON block: {"suggested_questions": ["...", "..."]}
"""


def get_openai_client():
    return AsyncAzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2024-02-01"
    )


def build_context_block(parent_sections: list[dict]) -> str:
    """Format parent sections into a context block for the LLM prompt."""
    blocks = []
    for i, section in enumerate(parent_sections, 1):
        heading = section.get("heading", "Section")
        text = section.get("full_text", "")
        url = section.get("source_url", "")
        blocks.append(
            f"[Context {i}]\nSection: {heading}\nSource: {url}\n\n{text}"
        )
    return "\n\n---\n\n".join(blocks)


async def stream_answer(
    query: str,
    parent_sections: list[dict],
    history: list[dict]
) -> AsyncGenerator[str, None]:
    """Stream GPT-4o response token by token."""
    client = get_openai_client()
    context_block = build_context_block(parent_sections)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"HR Policy Context:\n\n{context_block}"}
    ]

    # Inject last 3 turns
    messages.extend(history[-6:])

    # Current query
    messages.append({"role": "user", "content": query})

    stream = await client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        messages=messages,
        stream=True,
        temperature=0,
        max_tokens=1000
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content
