# =============================================================================
# agents/px4_search_agent/agent.py
# =============================================================================
# 🎯 Purpose:
# This file defines a simple AI agent called PX4SearchAgent.
# It uses Google's ADK and Gemini model to search PX4 documentation using a user query.
# =============================================================================


# -----------------------------------------------------------------------------
# 📦 Built-in & External Library Imports
# -----------------------------------------------------------------------------

import requests  # For making the search API call

# 🧠 Gemini-based AI agent provided by Google's ADK
from google.adk.agents.llm_agent import LlmAgent

# 📚 ADK services for session, memory, and file-like "artifacts"
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService

# 🏃 The "Runner" connects the agent, session, memory, and files into a complete system
from google.adk.runners import Runner

# 🧾 Gemini-compatible types for formatting input/output messages
from google.genai import types

# 🔐 Load environment variables (like API keys) from a `.env` file
from dotenv import load_dotenv
import os
load_dotenv()  # Load variables like SERPAPI_KEY into the system

# -----------------------------------------------------------------------------
# 🔍 PX4SearchAgent: AI agent that searches PX4 documentation
# -----------------------------------------------------------------------------

class PX4SearchAgent:
    # This agent only supports plain text input/output
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """
        👷 Initialize the PX4SearchAgent:
        - Creates the LLM agent (powered by Gemini)
        - Sets up session handling, memory, and a runner to execute tasks
        """
        self._agent = self._build_agent()
        self._user_id = "px4_search_user"

        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService()
        )

        # 🔑 Read your SERP API key from .env
        self.api_key = os.getenv("SERPAPI_KEY")

    def _build_agent(self) -> LlmAgent:
        """
        ⚙️ Creates and returns a Gemini agent with basic settings.

        Returns:
            LlmAgent: An agent object from Google's ADK
        """
        return LlmAgent(
            model="gemini-1.5-flash-latest",
            name="px4_search_agent",
            description="Searches PX4 documentation via Google Search API",
            instruction="Use the SERP API to find the most relevant PX4 documentation result for the user's query."
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """
        📥 Handle a user query and return a relevant PX4 documentation link.

        Args:
            query (str): The search phrase (e.g., "PX4 GPS setup")
            session_id (str): A session identifier

        Returns:
            str: Agent’s response with title, snippet, and link
        """
        # Try to reuse an existing session (or create one if needed)
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id
        )

        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
                state={}
            )

        # Call the SERP API to get PX4 documentation results
        try:
            response = requests.get("https://serpapi.com/search", params={
                "engine": "google",
                "q": f"{query} site:px4.io",
                "api_key": self.api_key
            })
            data = response.json()
            results = data.get("organic_results", [])

            if results:
                top = results[0]
                title = top.get("title", "No title")
                snippet = top.get("snippet", "")
                link = top.get("link", "")
                return f"**{title}**\n{snippet}\n{link}"
            else:
                return "No relevant PX4 results found."

        except Exception as e:
            return f"Error during search: {str(e)}"

    async def stream(self, query: str, session_id: str):
        """
        🌀 Provides a fallback 'stream' method for compatibility.
        Although this agent does not support real-time streaming,
        this method mimics streaming by returning a full result as a single chunk.

        Args:
            query (str): The user's search query for PX4 documentation
            session_id (str): Session identifier used for context tracking

        Yields:
            dict: A single dictionary containing the full response
        """

        # 🧠 Reuse the same logic as `invoke()` to perform the actual search
        result = await self.invoke(query, session_id)

        # 📤 Yield a single response indicating task completion
        # This is required for compatibility with A2A interfaces that expect a stream method
        yield {
            "is_task_complete": True,
            "content": result
        }

