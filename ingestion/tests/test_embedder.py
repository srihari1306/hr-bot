"""Tests for embedder module — these require Azure OpenAI credentials so are skipped by default."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.skipif(
    not os.environ.get("AZURE_OPENAI_KEY"),
    reason="Azure OpenAI credentials not configured"
)
@pytest.mark.asyncio
async def test_embed_texts():
    from pipeline.embedder import embed_texts
    vectors = await embed_texts(["Hello world", "Test embedding"])
    assert len(vectors) == 2
    assert len(vectors[0]) > 0  # Should be 1536 or 3072 dimensions
    assert all(isinstance(v, float) for v in vectors[0])
