"""Tests for ai_generator.py (AIGenerator)."""
import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestAIGenerator:
    """Tests for AIGenerator."""

    @patch('ai_generator.anthropic.Anthropic')
    def test_initialization(self, mock_anthropic_class):
        """Test AIGenerator initialization."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")

        assert generator.client == mock_client
        assert generator.model == "claude-sonnet-4-20250514"
        mock_anthropic_class.assert_called_once_with(api_key="test_key")

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_without_tools(self, mock_anthropic_class):
        """Test generate_response for a query that doesn't require tools."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock response without tool use
        mock_response = MagicMock()
        text_block = MagicMock()
        text_block.text = "Machine learning is a subset of artificial intelligence."
        mock_response.content = [text_block]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")

        result = generator.generate_response("What is machine learning?")

        assert result == "Machine learning is a subset of artificial intelligence."
        assert mock_client.messages.create.call_count == 1

    @patch('ai_generator.anthropic.Anthropic')
    def test_generate_response_with_tool_use(self, mock_anthropic_class, mock_vector_store, sample_search_results):
        """Test generate_response with tool calling."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock first response with tool use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "search_course_content"
        tool_block.id = "tool_12345"
        tool_block.input = {"query": "What is RAG?"}

        first_response = MagicMock()
        first_response.content = [tool_block]
        first_response.stop_reason = "tool_use"

        # Mock second response with final answer
        final_text_block = MagicMock()
        final_text_block.text = "Based on the search, RAG is Retrieval-Augmented Generation."
        second_response = MagicMock()
        second_response.content = [final_text_block]
        second_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [first_response, second_response]

        # Set up tool manager with search tool
        mock_vector_store.search.return_value = sample_search_results
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        generator = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")

        result = generator.generate_response(
            "What is RAG?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert result == "Based on the search, RAG is Retrieval-Augmented Generation."
        assert mock_client.messages.create.call_count == 2

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_error_handling(self, mock_anthropic_class, mock_vector_store):
        """Test that tool execution errors are handled gracefully."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock first response with tool use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "search_course_content"
        tool_block.id = "tool_12345"
        tool_block.input = {"query": "What is RAG?"}

        first_response = MagicMock()
        first_response.content = [tool_block]
        first_response.stop_reason = "tool_use"

        # Mock second response
        final_text_block = MagicMock()
        final_text_block.text = "I encountered an error while searching."
        second_response = MagicMock()
        second_response.content = [final_text_block]
        second_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [first_response, second_response]

        # Set up tool that raises exception
        mock_vector_store.search.side_effect = Exception("Database connection error")
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        generator = AIGenerator(api_key="test_key", model="claude-sonnet-4-20250514")

        # Should not raise exception, but handle it gracefully
        result = generator.generate_response(
            "What is RAG?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert isinstance(result, str)
        # Check that the error was passed to Claude as a tool result
        second_call = mock_client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]
        tool_result_content = messages[-1]["content"][0]["content"]
        assert "Tool execution error" in tool_result_content or "Search tool error" in tool_result_content
