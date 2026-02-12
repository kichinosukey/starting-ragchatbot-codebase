from typing import Dict, Any, Optional, Protocol, List
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults
from models import Source
import json


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "What to search for in the course content"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """
        try:
            # Use the vector store's unified search interface
            results = self.store.search(
                query=query,
                course_name=course_name,
                lesson_number=lesson_number
            )

            # Handle errors
            if results.error:
                return results.error

            # Handle empty results
            if results.is_empty():
                filter_info = ""
                if course_name:
                    filter_info += f" in course '{course_name}'"
                if lesson_number:
                    filter_info += f" in lesson {lesson_number}"
                return f"No relevant content found{filter_info}."

            # Format and return results
            return self._format_results(results)
        except Exception as e:
            # Catch any unexpected errors and return as string
            return f"Search tool error: {str(e)}"
    
    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI
        seen_sources = set()  # Deduplicate sources

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')

            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Create unique key for deduplication
            source_key = f"{course_title}_{lesson_num}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)

                # Get course link from vector store
                course_link = self.store.get_course_link(course_title)

                # Get lesson link and title if lesson number exists
                lesson_link = None
                lesson_title = None
                if lesson_num is not None:
                    lesson_link = self.store.get_lesson_link(course_title, lesson_num)
                    # Get lesson title from course metadata
                    lesson_title = self._get_lesson_title(course_title, lesson_num)

                # Create Source object with metadata
                source = Source(
                    course_title=course_title,
                    course_link=course_link,
                    lesson_number=lesson_num,
                    lesson_title=lesson_title,
                    lesson_link=lesson_link,
                    citation_number=len(sources) + 1  # Sequential numbering
                )
                sources.append(source)

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)

    def _get_lesson_title(self, course_title: str, lesson_number: int) -> Optional[str]:
        """Get lesson title from vector store metadata"""
        try:
            results = self.store.course_catalog.get(ids=[course_title])
            if results and 'metadatas' in results and results['metadatas']:
                metadata = results['metadatas'][0]
                lessons_json = metadata.get('lessons_json')
                if lessons_json:
                    lessons = json.loads(lessons_json)
                    for lesson in lessons:
                        if lesson.get('lesson_number') == lesson_number:
                            return lesson.get('lesson_title')
        except Exception as e:
            print(f"Error getting lesson title: {e}")
        return None


class CourseOutlineTool(Tool):
    """Tool for retrieving complete course outlines with lesson lists"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Maintain consistency with CourseSearchTool

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "get_course_outline",
            "description": "Retrieve the complete outline of a course including its title, link, and full list of lessons. Use this when users ask about course structure, lessons list, course content overview, or what topics a course covers.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title or partial name (fuzzy matching supported, e.g., 'MCP', 'prompt engineering')"
                    }
                },
                "required": ["course_name"]
            }
        }

    def execute(self, course_name: str) -> str:
        """Execute the outline tool to retrieve course structure"""
        try:
            # Step 1: Resolve course name using semantic search
            course_title = self.store._resolve_course_name(course_name)

            if not course_title:
                return f"No course found matching '{course_name}'. Please try a different course name or check available courses."

            # Step 2: Retrieve course metadata from catalog
            results = self.store.course_catalog.get(ids=[course_title])

            if not results or 'metadatas' not in results or not results['metadatas']:
                return f"Course '{course_title}' exists but has no metadata available."

            metadata = results['metadatas'][0]

            # Step 3: Extract and parse course data
            course_link = metadata.get('course_link', 'No link available')
            instructor = metadata.get('instructor', 'Unknown')
            lessons_json = metadata.get('lessons_json')

            # Step 4: Parse lessons JSON
            if not lessons_json:
                return f"Course '{course_title}' has no lessons information available."

            lessons = json.loads(lessons_json)

            if not lessons:
                return f"Course '{course_title}' has an empty lessons list."

            # Step 5: Format the output
            return self._format_outline(course_title, course_link, instructor, lessons)

        except json.JSONDecodeError as e:
            return f"Error parsing lessons data for course '{course_name}': {str(e)}"
        except Exception as e:
            return f"Error retrieving course outline: {str(e)}"

    def _format_outline(self, title: str, course_link: str, instructor: str, lessons: List[Dict]) -> str:
        """Format the course outline for presentation"""
        # Build header
        output = [f"Course: {title}"]

        if course_link and course_link != 'No link available':
            output.append(f"Link: {course_link}")

        if instructor and instructor != 'Unknown':
            output.append(f"Instructor: {instructor}")

        # Add lessons section
        output.append(f"\nLessons ({len(lessons)} total):")

        # Sort lessons by lesson_number to ensure correct order
        sorted_lessons = sorted(lessons, key=lambda x: x.get('lesson_number', 0))

        for lesson in sorted_lessons:
            lesson_num = lesson.get('lesson_number', '?')
            lesson_title = lesson.get('lesson_title', 'Untitled')
            lesson_link = lesson.get('lesson_link')

            # Format each lesson with link
            lesson_line = f"  {lesson_num}. {lesson_title}"
            if lesson_link:
                lesson_line += f" - {lesson_link}"

            output.append(lesson_line)

        return "\n".join(output)


class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        return self.tools[tool_name].execute(**kwargs)
    
    def get_last_sources(self) -> List[Source]:
        """Get sources from the last search operation and reset them"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                sources = tool.last_sources.copy()
                tool.last_sources = []  # Reset after retrieval
                return sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []