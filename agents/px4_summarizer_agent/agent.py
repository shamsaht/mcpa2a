# =============================================================================
# agents/px4_summarizer_agent/agent.py
# =============================================================================
# 🎯 Purpose:
# This file defines a simple AI agent called PX4SummarizerAgent.
# It uses Google's ADK and Gemini model to fetch and summarize PX4 documentation
# based on a natural language user query.
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
from bs4 import BeautifulSoup  # For parsing HTML content

load_dotenv()  # Load variables like SERPAPI_KEY into the system

# -----------------------------------------------------------------------------
# 📄 PX4SummarizerAgent: AI agent that fetches and summarizes PX4 documentation
# -----------------------------------------------------------------------------

class PX4SummarizerAgent:
    # This agent only supports plain text input/output
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """
        👷 Initialize the PX4SummarizerAgent:
        - Creates the LLM agent (powered by Gemini)
        - Sets up session handling, memory, and a runner to execute tasks
        """
        self._agent = self._build_agent()
        self._user_id = "px4_summarizer_user"

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
        ⚙️ Creates and returns a Gemini agent with summarization settings.

        Returns:
            LlmAgent: An agent object from Google's ADK
        """
        return LlmAgent(
            model="gemini-1.5-flash-latest",
            name="px4_summarizer_agent",
            description="Summarizes technical PX4 documentation from web content.",
            instruction="You are a technical summarizer. Read PX4 documentation and respond with a clear, concise summary."
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """
        📥 Handle a user query by fetching and summarizing PX4 documentation.

        Args:
            query (str): The search phrase (e.g., "PX4 offboard mode")
            session_id (str): A session identifier

        Returns:
            str: Agent’s summarized response
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

        try:
            # 🔍 Step 1: Search for PX4 docs via SERP API
            response = requests.get("https://serpapi.com/search", params={
                "engine": "google",
                "q": f"{query} site:px4.io",
                "api_key": self.api_key
            })
            data = response.json()
            results = data.get("organic_results", [])

            if not results:
                return "No relevant PX4 documentation found."

            top_result = results[0]
            link = top_result.get("link")
            if not link:
                return "PX4 documentation link not found."

            # 🌐 Step 2: Fetch the content of the PX4 doc page
            html_page = requests.get(link, timeout=10).text
            soup = BeautifulSoup(html_page, "html.parser")
            main_content = soup.get_text(separator="\n")  # Simplified plain-text extraction

            # ✂️ Step 3: Truncate overly long content
            if len(main_content) > 8000:
                main_content = main_content[:8000]

            # 🧠 Step 4: Ask Gemini to summarize

            summary_prompt = f"Summarize the following PX4 documentation content for a technical audience:\n\n{main_content}"

            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=summary_prompt)]
            )

            last_event = None
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=content
            ):
                last_event = event

            if not last_event or not last_event.content or not last_event.content.parts:
                return "Failed to generate summary."

            return "\n".join([p.text for p in last_event.content.parts if p.text])

        except Exception as e:
            return f"Error while summarizing PX4 documentation: {str(e)}"

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

        # 🧠 Reuse the same logic as `invoke()` to perform the actual work
        result = await self.invoke(query, session_id)

        # 📤 Yield a single response indicating task completion
        yield {
            "is_task_complete": True,
            "content": result
        }
