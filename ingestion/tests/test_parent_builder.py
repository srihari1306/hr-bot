import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.parent_builder import build_parent_sections


def test_single_section():
    """Test building sections from a document with no headings."""
    structure = {
        "elements": [
            {"type": "paragraph", "level": None, "content": "Some policy text.", "page": 1},
            {"type": "paragraph", "level": None, "content": "More policy text.", "page": 1},
        ]
    }
    sections = build_parent_sections(structure, "doc1", "Test Policy", "test.pdf")
    assert len(sections) == 1
    assert sections[0].heading == "Test Policy"


def test_multiple_sections():
    """Test building sections from a document with headings."""
    structure = {
        "elements": [
            {"type": "heading", "level": 1, "content": "Leave Policy", "page": 1},
            {"type": "paragraph", "level": None, "content": "Leave details here.", "page": 1},
            {"type": "heading", "level": 2, "content": "Annual Leave", "page": 2},
            {"type": "paragraph", "level": None, "content": "You get 20 days.", "page": 2},
        ]
    }
    sections = build_parent_sections(structure, "doc1", "Test Policy", "test.pdf")
    assert len(sections) == 2
    assert sections[0].heading == "Leave Policy"
    assert sections[1].heading == "Annual Leave"


def test_empty_document():
    """Test building sections from an empty document."""
    structure = {"elements": []}
    sections = build_parent_sections(structure, "doc1", "Empty", "test.pdf")
    assert len(sections) == 0
