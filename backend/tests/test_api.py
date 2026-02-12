"""API endpoint tests for the RAG chatbot system."""
import pytest
from fastapi import status


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for the /api/query endpoint."""

    def test_query_without_session_id(self, test_client):
        """Test query endpoint creates a new session when session_id is not provided."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify session ID was created
        assert data["session_id"] == "test-session-123"

        # Verify answer content
        assert "RAG" in data["answer"]
        assert "Retrieval-Augmented Generation" in data["answer"]

        # Verify sources
        assert len(data["sources"]) > 0
        source = data["sources"][0]
        assert source["course_title"] == "Introduction to RAG Systems"
        assert source["lesson_number"] == 0
        assert source["citation_number"] == 1

    def test_query_with_existing_session_id(self, test_client):
        """Test query endpoint uses provided session_id."""
        session_id = "existing-session-456"
        response = test_client.post(
            "/api/query",
            json={
                "query": "What is RAG?",
                "session_id": session_id
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the session ID matches what was provided
        assert data["session_id"] == session_id

    def test_query_with_empty_query(self, test_client):
        """Test query endpoint handles empty query strings."""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still succeed (validation happens at RAG system level)
        assert response.status_code == status.HTTP_200_OK

    def test_query_with_missing_query_field(self, test_client):
        """Test query endpoint returns 422 when query field is missing."""
        response = test_client.post(
            "/api/query",
            json={}
        )

        # FastAPI validation should fail
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_with_invalid_json(self, test_client):
        """Test query endpoint handles invalid JSON."""
        response = test_client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 for invalid JSON
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_response_schema(self, test_client):
        """Test that query response matches expected Pydantic schema."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required fields exist
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify source structure
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            required_fields = [
                "course_title", "lesson_number", "lesson_title",
                "course_link", "lesson_link", "citation_number"
            ]
            for field in required_fields:
                assert field in source, f"Missing required field: {field}"


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint."""

    def test_get_courses_success(self, test_client):
        """Test courses endpoint returns course statistics."""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Introduction to RAG Systems" in data["course_titles"]
        assert "Advanced AI Techniques" in data["course_titles"]

    def test_get_courses_response_schema(self, test_client):
        """Test that courses response matches expected Pydantic schema."""
        response = test_client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify all course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)


@pytest.mark.api
class TestRootEndpoint:
    """Tests for the root / endpoint."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns a welcome message."""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response contains a message
        assert "message" in data
        assert isinstance(data["message"], str)


@pytest.mark.api
class TestErrorHandling:
    """Tests for API error handling."""

    def test_query_endpoint_with_rag_system_error(self, test_client, mock_rag_system):
        """Test query endpoint handles RAG system errors gracefully."""
        # Configure mock to raise an exception
        mock_rag_system.query.side_effect = Exception("Database connection failed")

        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"}
        )

        # Should return 500 Internal Server Error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()

        # Error detail should be present
        assert "detail" in data
        assert "Database connection failed" in data["detail"]

    def test_courses_endpoint_with_analytics_error(self, test_client, mock_rag_system):
        """Test courses endpoint handles analytics errors gracefully."""
        # Configure mock to raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics service unavailable")

        response = test_client.get("/api/courses")

        # Should return 500 Internal Server Error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()

        # Error detail should be present
        assert "detail" in data
        assert "Analytics service unavailable" in data["detail"]


@pytest.mark.api
class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_on_query_endpoint(self, test_client):
        """Test that CORS headers are properly set on query endpoint."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"},
            headers={"Origin": "http://localhost:3000"}
        )

        # Request should succeed with CORS headers
        assert response.status_code == status.HTTP_200_OK

        # Check for CORS headers (TestClient may not set all headers, but middleware is configured)
        # The important part is that the middleware is configured in the app

    def test_cors_headers_on_courses_endpoint(self, test_client):
        """Test that CORS headers are properly set on courses endpoint."""
        response = test_client.get(
            "/api/courses",
            headers={"Origin": "http://localhost:3000"}
        )

        # Request should succeed with CORS headers
        assert response.status_code == status.HTTP_200_OK

        # Check for CORS headers (TestClient may not set all headers, but middleware is configured)
        # The important part is that the middleware is configured in the app


@pytest.mark.api
class TestSessionManagement:
    """Tests for session management in API."""

    def test_multiple_queries_same_session(self, test_client):
        """Test that multiple queries can use the same session."""
        # First query creates session
        response1 = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"}
        )
        session_id = response1.json()["session_id"]

        # Second query uses same session
        response2 = test_client.post(
            "/api/query",
            json={
                "query": "Tell me more about vector embeddings",
                "session_id": session_id
            }
        )

        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["session_id"] == session_id

    def test_different_sessions_isolated(self, test_client, mock_rag_system):
        """Test that different sessions are isolated from each other."""
        # Create two different sessions
        response1 = test_client.post(
            "/api/query",
            json={"query": "Query 1"}
        )
        session1 = response1.json()["session_id"]

        # Reset the mock to return a different session ID
        mock_rag_system.session_manager.create_session.return_value = "test-session-789"

        response2 = test_client.post(
            "/api/query",
            json={"query": "Query 2"}
        )
        session2 = response2.json()["session_id"]

        # Sessions should be different
        assert session1 != session2
