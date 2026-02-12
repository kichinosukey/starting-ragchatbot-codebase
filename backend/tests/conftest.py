"""Shared test fixtures for the RAG chatbot test suite."""

import sys
from pathlib import Path

# Add backend directory to sys.path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from unittest.mock import MagicMock
from models import Course, Lesson, Source
from vector_store import SearchResults


@pytest.fixture
def sample_course():
    """Create a sample course for testing."""
    return Course(
        title="Introduction to RAG Systems",
        instructor="Dr. Jane Smith",
        link="https://example.com/rag-course",
        lessons=[
            Lesson(
                lesson_number=0,
                title="What is RAG?",
                link="https://example.com/rag-course/lesson-0",
            ),
            Lesson(
                lesson_number=1,
                title="Vector Embeddings",
                link="https://example.com/rag-course/lesson-1",
            ),
            Lesson(
                lesson_number=2,
                title="Semantic Search",
                link="https://example.com/rag-course/lesson-2",
            ),
        ],
    )


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return SearchResults(
        documents=[
            "RAG stands for Retrieval-Augmented Generation. It combines information retrieval with text generation.",
            "Vector embeddings are numerical representations of text that capture semantic meaning.",
            "Semantic search finds results based on meaning rather than exact keyword matches.",
        ],
        metadata=[
            {
                "course_title": "Introduction to RAG Systems",
                "lesson_number": 0,
                "lesson_title": "What is RAG?",
                "course_link": "https://example.com/rag-course",
                "lesson_link": "https://example.com/rag-course/lesson-0",
            },
            {
                "course_title": "Introduction to RAG Systems",
                "lesson_number": 1,
                "lesson_title": "Vector Embeddings",
                "course_link": "https://example.com/rag-course",
                "lesson_link": "https://example.com/rag-course/lesson-1",
            },
            {
                "course_title": "Introduction to RAG Systems",
                "lesson_number": 2,
                "lesson_title": "Semantic Search",
                "course_link": "https://example.com/rag-course",
                "lesson_link": "https://example.com/rag-course/lesson-2",
            },
        ],
        distances=[0.1, 0.2, 0.3],
    )


@pytest.fixture
def sample_sources():
    """Create sample sources for testing."""
    return [
        Source(
            course_title="Introduction to RAG Systems",
            lesson_number=0,
            lesson_title="What is RAG?",
            course_link="https://example.com/rag-course",
            lesson_link="https://example.com/rag-course/lesson-0",
            citation_number=1,
        ),
        Source(
            course_title="Introduction to RAG Systems",
            lesson_number=1,
            lesson_title="Vector Embeddings",
            course_link="https://example.com/rag-course",
            lesson_link="https://example.com/rag-course/lesson-1",
            citation_number=2,
        ),
    ]


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore for testing."""
    mock = MagicMock()

    # Mock search method
    mock.search.return_value = SearchResults(
        documents=[
            "RAG stands for Retrieval-Augmented Generation.",
            "It combines retrieval with generation.",
        ],
        metadata=[
            {
                "course_title": "Introduction to RAG Systems",
                "lesson_number": 0,
                "lesson_title": "What is RAG?",
                "course_link": "https://example.com/rag-course",
                "lesson_link": "https://example.com/rag-course/lesson-0",
            },
            {
                "course_title": "Introduction to RAG Systems",
                "lesson_number": 1,
                "lesson_title": "Vector Embeddings",
                "course_link": "https://example.com/rag-course",
                "lesson_link": "https://example.com/rag-course/lesson-1",
            },
        ],
        distances=[0.1, 0.2],
    )

    # Mock get_all_courses method
    mock.get_all_courses.return_value = [
        Course(
            title="Introduction to RAG Systems",
            instructor="Dr. Jane Smith",
            course_link="https://example.com/rag-course",
            lessons=[
                Lesson(
                    lesson_number=0,
                    title="What is RAG?",
                    lesson_link="https://example.com/rag-course/lesson-0",
                ),
                Lesson(
                    lesson_number=1,
                    title="Vector Embeddings",
                    lesson_link="https://example.com/rag-course/lesson-1",
                ),
            ],
        )
    ]

    # Mock _resolve_course_name method
    mock._resolve_course_name.return_value = "Introduction to RAG Systems"

    # Mock get_course_link method
    mock.get_course_link.return_value = "https://example.com/rag-course"

    # Mock get_lesson_link method
    mock.get_lesson_link.return_value = "https://example.com/rag-course/lesson-0"

    # Mock course_catalog for CourseOutlineTool
    mock_catalog = MagicMock()
    mock_catalog.get.return_value = {
        "metadatas": [
            {
                "course_link": "https://example.com/rag-course",
                "instructor": "Dr. Jane Smith",
                "lessons_json": '[{"lesson_number": 0, "lesson_title": "What is RAG?", "lesson_link": "https://example.com/rag-course/lesson-0"}, {"lesson_number": 1, "lesson_title": "Vector Embeddings", "lesson_link": "https://example.com/rag-course/lesson-1"}]',
            }
        ]
    }
    mock.course_catalog = mock_catalog

    return mock


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing."""
    mock = MagicMock()

    # Mock text response (no tool use)
    text_response = MagicMock()
    text_response.content = [
        MagicMock(type="text", text="This is a direct response without tool use.")
    ]
    text_response.stop_reason = "end_turn"

    # Mock tool use response
    tool_response = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "search_course_content"
    tool_block.id = "tool_12345"
    tool_block.input = {"query": "What is RAG?"}
    tool_response.content = [tool_block]
    tool_response.stop_reason = "tool_use"

    # Mock final response after tool use
    final_response = MagicMock()
    final_response.content = [
        MagicMock(
            type="text",
            text="Based on the search results, RAG stands for Retrieval-Augmented Generation.",
        )
    ]
    final_response.stop_reason = "end_turn"

    # Configure mock to return different responses on consecutive calls
    mock.messages.create.side_effect = [tool_response, final_response]

    return mock
