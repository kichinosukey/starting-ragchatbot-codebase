"""Tests for search_tools.py (CourseSearchTool and CourseOutlineTool)."""

import pytest
from unittest.mock import MagicMock, patch
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults
from models import Course, Lesson


class TestCourseSearchTool:
    """Tests for CourseSearchTool."""

    def test_get_tool_definition(self):
        """Test that the tool definition is properly formatted."""
        vector_store = MagicMock()
        tool = CourseSearchTool(vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]

    def test_execute_with_valid_query(self, mock_vector_store, sample_search_results):
        """Test execute with a valid query returns formatted results."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?")

        assert isinstance(result, str)
        assert "RAG stands for Retrieval-Augmented Generation" in result
        assert "[Introduction to RAG Systems" in result  # Course name in header
        mock_vector_store.search.assert_called_once()

    def test_execute_with_course_name_filter(
        self, mock_vector_store, sample_search_results
    ):
        """Test execute with course_name parameter."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?", course_name="RAG Systems")

        # VectorStore.search() handles course name resolution internally
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["course_name"] == "RAG Systems"

    def test_execute_with_lesson_number_filter(
        self, mock_vector_store, sample_search_results
    ):
        """Test execute with lesson_number parameter."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?", lesson_number=0)

        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["lesson_number"] == 0

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Test execute with both course_name and lesson_number."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?", course_name="RAG", lesson_number=0)

        # VectorStore.search() handles resolution internally
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["course_name"] == "RAG"
        assert call_args[1]["lesson_number"] == 0

    def test_execute_with_empty_results(self, mock_vector_store):
        """Test execute when no results are found."""
        mock_vector_store.search.return_value = SearchResults.empty("No results found")
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="Nonexistent topic")

        # When SearchResults has an error, it returns the error message directly
        assert "No results found" in result
        assert len(tool.last_sources) == 0

    def test_execute_with_invalid_course_name(self, mock_vector_store):
        """Test execute when course name cannot be resolved."""
        # VectorStore.search() returns error when course not found
        mock_vector_store.search.return_value = SearchResults.empty(
            "No course found matching 'Nonexistent Course'"
        )
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?", course_name="Nonexistent Course")

        assert "No course found matching" in result
        assert "Nonexistent Course" in result

    def test_execute_with_vector_store_exception(self, mock_vector_store):
        """Test execute when VectorStore raises an exception."""
        mock_vector_store.search.side_effect = Exception("Database connection error")
        tool = CourseSearchTool(mock_vector_store)

        # Exception is caught and returned as error message
        result = tool.execute(query="What is RAG?")

        assert "Search tool error" in result
        assert "Database connection error" in result

    def test_last_sources_tracking(self, mock_vector_store, sample_search_results):
        """Test that last_sources are correctly tracked."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="What is RAG?")

        assert len(tool.last_sources) == 3
        assert tool.last_sources[0].citation_number == 1
        assert tool.last_sources[0].course_title == "Introduction to RAG Systems"
        assert tool.last_sources[0].lesson_number == 0

    def test_sources_reset_on_new_query(self, mock_vector_store, sample_search_results):
        """Test that sources are reset for each new query."""
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="First query")
        first_sources_count = len(tool.last_sources)

        tool.execute(query="Second query")
        second_sources_count = len(tool.last_sources)

        assert first_sources_count == second_sources_count == 3


class TestCourseOutlineTool:
    """Tests for CourseOutlineTool."""

    def test_get_tool_definition(self):
        """Test that the tool definition is properly formatted."""
        vector_store = MagicMock()
        tool = CourseOutlineTool(vector_store)
        definition = tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        assert "course_name" in definition["input_schema"]["properties"]

    def test_execute_with_valid_course(self, mock_vector_store, sample_course):
        """Test execute with a valid course name."""
        mock_vector_store._resolve_course_name.return_value = (
            "Introduction to RAG Systems"
        )
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="RAG Systems")

        assert isinstance(result, str)
        assert "Introduction to RAG Systems" in result
        assert "Dr. Jane Smith" in result
        assert "What is RAG?" in result
        assert "Vector Embeddings" in result
        mock_vector_store._resolve_course_name.assert_called_once_with("RAG Systems")

    def test_execute_with_fuzzy_matching(self, mock_vector_store, sample_course):
        """Test execute with fuzzy course name matching."""
        mock_vector_store._resolve_course_name.return_value = (
            "Introduction to RAG Systems"
        )
        mock_vector_store.get_all_courses.return_value = [sample_course]
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="MCP")

        mock_vector_store._resolve_course_name.assert_called_once_with("MCP")
        assert "Introduction to RAG Systems" in result

    def test_execute_with_nonexistent_course(self, mock_vector_store):
        """Test execute when course name cannot be resolved."""
        mock_vector_store._resolve_course_name.return_value = None
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="Nonexistent Course")

        assert "No course found" in result
        assert "Nonexistent Course" in result

    def test_execute_with_course_not_in_list(self, mock_vector_store, sample_course):
        """Test execute when resolved course has no metadata."""
        mock_vector_store._resolve_course_name.return_value = "Different Course"
        # Mock catalog returns empty metadata
        mock_vector_store.course_catalog.get.return_value = {"metadatas": []}
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="Some Course")

        assert "no metadata available" in result

    def test_execute_with_exception(self, mock_vector_store):
        """Test execute when an exception occurs."""
        mock_vector_store._resolve_course_name.side_effect = Exception("Database error")
        tool = CourseOutlineTool(mock_vector_store)

        # Exception is caught and returned as error message
        result = tool.execute(course_name="RAG")

        assert "Error retrieving course outline" in result
        assert "Database error" in result

    def test_format_outline_sorting(self, mock_vector_store):
        """Test that lessons are sorted by lesson_number."""
        # Mock catalog with unsorted lessons
        mock_vector_store._resolve_course_name.return_value = "Test Course"
        mock_vector_store.course_catalog.get.return_value = {
            "metadatas": [
                {
                    "course_link": "https://example.com/course",
                    "instructor": "Test Instructor",
                    "lessons_json": '[{"lesson_number": 2, "lesson_title": "Third Lesson"}, {"lesson_number": 0, "lesson_title": "First Lesson"}, {"lesson_number": 1, "lesson_title": "Second Lesson"}]',
                }
            ]
        }
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="Test")

        # Check that lessons appear in correct order in the output
        lesson_0_pos = result.find("0. First Lesson")
        lesson_1_pos = result.find("1. Second Lesson")
        lesson_2_pos = result.find("2. Third Lesson")

        assert lesson_0_pos < lesson_1_pos < lesson_2_pos


class TestToolManager:
    """Tests for ToolManager."""

    def test_register_and_get_tools(self, mock_vector_store):
        """Test registering tools and getting their definitions."""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 2
        assert definitions[0]["name"] == "search_course_content"
        assert definitions[1]["name"] == "get_course_outline"

    def test_execute_tool(self, mock_vector_store, sample_search_results):
        """Test executing a registered tool."""
        mock_vector_store.search.return_value = sample_search_results
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        result = manager.execute_tool("search_course_content", query="What is RAG?")

        assert isinstance(result, str)
        assert "RAG" in result

    def test_execute_nonexistent_tool(self, mock_vector_store):
        """Test executing a tool that doesn't exist."""
        manager = ToolManager()

        with pytest.raises(ValueError) as exc_info:
            manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in str(exc_info.value).lower()

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test getting sources from the last search."""
        mock_vector_store.search.return_value = sample_search_results
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        manager.execute_tool("search_course_content", query="What is RAG?")
        sources = manager.get_last_sources()

        assert len(sources) == 3
        assert all(hasattr(source, "citation_number") for source in sources)

    def test_sources_reset_after_retrieval(
        self, mock_vector_store, sample_search_results
    ):
        """Test that sources are reset after retrieval."""
        mock_vector_store.search.return_value = sample_search_results
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        manager.execute_tool("search_course_content", query="What is RAG?")
        first_sources = manager.get_last_sources()
        second_sources = manager.get_last_sources()

        assert len(first_sources) == 3
        assert len(second_sources) == 0  # Should be reset after first retrieval
