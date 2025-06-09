# =============================================================================
# agents/px4_command_agent/agent.py
# =============================================================================
# 🎯 Purpose:
# This file defines a simple AI agent called PX4CommandAgent.
# It uses Google's ADK and Gemini model to convert user input into PX4 shell commands.
# =============================================================================


# -----------------------------------------------------------------------------
# 📦 Built-in & External Library Imports
# -----------------------------------------------------------------------------

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
load_dotenv()  # Load variables into the system
# This allows you to keep sensitive data out of your code.

# -----------------------------------------------------------------------------
# 🔧 PX4CommandAgent: AI agent that generates PX4 CLI commands from user input
# -----------------------------------------------------------------------------

class PX4CommandAgent:
    # This agent only supports plain text input/output
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """
        👷 Initialize the PX4CommandAgent:
        - Creates the LLM agent (powered by Gemini)
        - Sets up session handling, memory, and a runner to execute tasks
        """
        self._agent = self._build_agent()
        self._user_id = "px4_command_user"

        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService()
        )

    def _build_agent(self) -> LlmAgent:
        """
        ⚙️ Creates and returns a Gemini agent with PX4 command generation logic.

        Returns:
            LlmAgent: An agent object from Google's ADK
        """
        return LlmAgent(
            model="gemini-1.5-flash-latest",
            name="px4_command_agent",
            description="Generates PX4-compatible shell commands from user input.",
            instruction=(
                "You are a PX4 shell assistant. Your job is to translate user input into a single valid PX4 shell command. "
                "Respond with only the PX4 NSH or MAVLink command that should be executed — no explanation, no formatting, no markdown, and no extra output. "
                "Example: if the user says 'arm the drone', return 'commander arm'."
            )
        
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """
        📥 Handle a user query and return the corresponding PX4 shell command.

        Args:
            query (str): The user instruction (e.g., "Disarm the drone")
            session_id (str): A session identifier

        Returns:
            str: PX4 command as plain text
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

        # Ask Gemini to convert the user query into a PX4 command
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(query)]
        )

        last_event = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=content
        ):
            last_event = event

        # 🧹 Fallback: return empty string if something went wrong
        if not last_event or not last_event.content or not last_event.content.parts:
            return "Unable to generate command."

        # 📤 Extract and join all text responses into one string
        return "\n".join([p.text for p in last_event.content.parts if p.text])

    async def stream(self, query: str, session_id: str):
        """
        🌀 Provides a fallback 'stream' method for compatibility.
        Although this agent does not support real-time streaming,
        this method mimics streaming by returning a full result as a single chunk.

        Args:
            query (str): The user's instruction to convert
            session_id (str): Session identifier used for context tracking

        Yields:
            dict: A single dictionary containing the full response
        """
        result = await self.invoke(query, session_id)

        yield {
            "is_task_complete": True,
            "content": result
        }
