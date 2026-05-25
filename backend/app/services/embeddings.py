import os
from openai import AsyncAzureOpenAI

_client = None


def get_openai_client():
    global _client
    if not _client:
        _client = AsyncAzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version="2024-02-01"
        )
    return _client


async def embed_query(text: str) -> list[float]:
    """Embed a single query string for search."""
    client = get_openai_client()
    response = await client.embeddings.create(
        model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
        input=text
    )
    return response.data[0].embedding
