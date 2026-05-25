import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.models import ParentSection
from pipeline.chunker import chunk_section


def test_basic_chunking():
    """Test that a simple parent section gets chunked correctly."""
    section = ParentSection(
        document_id="test-doc",
        section_id="test-section",
        heading="Test Section",
        full_text="This is paragraph one about leave policy.\n\nThis is paragraph two about annual leave details.",
        page_range=(1, 1),
        source_url="test.pdf"
    )
    chunks = chunk_section(section, "Test Document")
    assert len(chunks) >= 1
    assert all(c.document_id == "test-doc" for c in chunks)
    assert all(c.section_id == "test-section" for c in chunks)
    assert all(c.chunk_type == "text" for c in chunks)


def test_table_chunk():
    """Test that table content gets its own chunk with type 'table'."""
    table_text = "Header1 | Header2 | Header3\nRow1Col1 | Row1Col2 | Row1Col3\nRow2Col1 | Row2Col2 | Row2Col3"
    section = ParentSection(
        document_id="test-doc",
        section_id="test-section",
        heading="Benefits Table",
        full_text=table_text,
        page_range=(2, 2),
        source_url="test.pdf"
    )
    chunks = chunk_section(section, "Test Document")
    assert len(chunks) >= 1
    # The table should be detected as a table chunk
    table_chunks = [c for c in chunks if c.chunk_type == "table"]
    assert len(table_chunks) >= 1


def test_empty_section():
    """Test that an empty section produces no chunks."""
    section = ParentSection(
        document_id="test-doc",
        section_id="test-section",
        heading="Empty",
        full_text="",
        page_range=(1, 1),
        source_url="test.pdf"
    )
    chunks = chunk_section(section, "Test Document")
    assert len(chunks) == 0
