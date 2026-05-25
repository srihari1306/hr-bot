import asyncio
import os
from openai import AsyncAzureOpenAI
from schemas.models import ChildChunk

client = AsyncAzureOpenAI(
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
    api_version="2024-02-01"
)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed with retry on rate limit."""
    BATCH_SIZE = 16
    all_vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        for attempt in range(5):
            try:
                response = await client.embeddings.create(
                    model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
                    input=batch
                )
                all_vectors.extend([r.embedding for r in response.data])
                break
            except Exception as e:
                if "429" in str(e):
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    return all_vectors


async def embed_chunks(chunks: list[ChildChunk]) -> list[ChildChunk]:
    """Embed all child chunks and attach vectors."""
    texts = [c.content for c in chunks]
    vectors = await embed_texts(texts)
    for chunk, vec in zip(chunks, vectors):
        chunk.content_vector = vec
    return chunks
