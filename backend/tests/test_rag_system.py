"""Tests for rag_system.py (RAGSystem end-to-end integration)."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from rag_system import RAGSystem
from vector_store import SearchResults


class TestRAGSystem:
    """Tests for RAGSystem integration."""

    @patch("rag_system.SessionManager")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_initialization(
        self,
        mock_doc_proc_class,
        mock_vector_store_class,
        mock_ai_gen_class,
        mock_session_mgr_class,
    ):
        """Test RAGSystem initialization."""
        from config import Config

        config = Config()

        rag = RAGSystem(config)

        # Verify all components were initialized
        assert rag.config == config
        mock_doc_proc_class.assert_called_once()
        mock_vector_store_class.assert_called_once()
        mock_ai_gen_class.assert_called_once()
        mock_session_mgr_class.assert_called_once()

    @patch("rag_system.SessionManager")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_query_without_session_id(
        self,
        mock_doc_proc_class,
        mock_vector_store_class,
        mock_ai_gen_class,
        mock_session_mgr_class,
    ):
        """Test querying without providing a session ID."""
        from config import Config

        config = Config()

        mock_session_mgr = MagicMock()
        mock_session_mgr.get_conversation_history.return_value = (
            None  # No session history
        )
        mock_session_mgr_class.return_value = mock_session_mgr

        mock_ai_gen = MagicMock()
        mock_ai_gen.generate_response.return_value = "This is the response."
        mock_ai_gen_class.return_value = mock_ai_gen

        rag = RAGSystem(config)
        response, sources = rag.query("What is RAG?")

        assert response == "This is the response."
        assert isinstance(sources, list)
        # Note: Session creation is handled by app.py, not RAGSystem

    @patch("rag_system.SessionManager")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_query_with_existing_session_id(
        self,
        mock_doc_proc_class,
        mock_vector_store_class,
        mock_ai_gen_class,
        mock_session_mgr_class,
    ):
        """Test querying with an existing session ID."""
        from config import Config

        config = Config()

        mock_session_mgr = MagicMock()
        conversation_history = "Previous question\n\nPrevious answer"
        mock_session_mgr.get_conversation_history.return_value = conversation_history
        mock_session_mgr_class.return_value = mock_session_mgr

        mock_ai_gen = MagicMock()
        mock_ai_gen.generate_response.return_value = "Follow-up response."
        mock_ai_gen_class.return_value = mock_ai_gen

        rag = RAGSystem(config)
        response, sources = rag.query("Tell me more", session_id="session_12345")

        assert response == "Follow-up response."
        mock_session_mgr.get_conversation_history.assert_called_once_with(
            "session_12345"
        )
        # Verify history was passed to AIGenerator
        mock_ai_gen.generate_response.assert_called_once()
        call_args = mock_ai_gen.generate_response.call_args
        assert call_args[1]["conversation_history"] == conversation_history

    @patch("rag_system.SessionManager")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_query_updates_session_history(
        self,
        mock_doc_proc_class,
        mock_vector_store_class,
        mock_ai_gen_class,
        mock_session_mgr_class,
    ):
        """Test that session history is updated after a query."""
        from config import Config

        config = Config()

        mock_session_mgr = MagicMock()
        mock_session_mgr.create_session.return_value = "session_12345"
        mock_session_mgr.get_conversation_history.return_value = []
        mock_session_mgr_class.return_value = mock_session_mgr

        mock_ai_gen = MagicMock()
        mock_ai_gen.generate_response.return_value = "Response text."
        mock_ai_gen_class.return_value = mock_ai_gen

        rag = RAGSystem(config)
        rag.query("Test query", session_id="session_12345")

        # Verify add_exchange was called once (with user query and assistant response)
        assert mock_session_mgr.add_exchange.call_count == 1
        call = mock_session_mgr.add_exchange.call_args

        assert call[0][0] == "session_12345"
        assert "Test query" in call[0][1]  # User message
        assert call[0][2] == "Response text."  # Assistant response

    @patch("rag_system.SessionManager")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_query_returns_sources(
        self,
        mock_doc_proc_class,
        mock_vector_store_class,
        mock_ai_gen_class,
        mock_session_mgr_class,
        sample_sources,
    ):
        """Test that sources are returned from tool usage."""
        from config import Config

        config = Config()

        mock_session_mgr = MagicMock()
        mock_session_mgr.create_session.return_value = "session_12345"
        mock_session_mgr.get_conversation_history.return_value = []
        mock_session_mgr_class.return_value = mock_session_mgr

        mock_ai_gen = MagicMock()
        mock_ai_gen.generate_response.return_value = "Response with sources."
        mock_ai_gen_class.return_value = mock_ai_gen

        rag = RAGSystem(config)
        # Mock tool manager to return sources
        rag.tool_manager.get_last_sources = MagicMock(return_value=sample_sources)

        response, sources = rag.query("What is RAG?")

        assert len(sources) == 2
        assert sources[0].course_title == "Introduction to RAG Systems"
        assert sources[0].citation_number == 1
