"""Session module — manages user context and conversation history for Finance Agent"""

from pathlib import Path
from datetime import datetime

from agent.state import DependencyState
from bridge.expense_bridge import ExpenseBridge


# file path for getting system prompt
SYSTEM_PROMPT_FILEPATH = Path(__file__).parent / "prompts" / "system_prompt.md"


class Session:
    """Maintains session context for a single user conversation.
    
    Holds user_id, username, bridge instance, conversation history,
    and session creation time. Created once at login and reused
    across all tool calls for that conversation.
    """

    def __init__(self, user_id: str, username: str, bridge: ExpenseBridge):
        """Initialize session with user context and empty history.
        
        Args:
            user_id:  Unique user identifier e.g. 'u001'
            username: Display name e.g. 'ram'
            bridge:   ExpenseBridge instance for this user
        """
        self.user_id = user_id
        self.username = username
        self.bridge = bridge
        self.history = []
        self.created_at = datetime.now()
        self.state = DependencyState()


    def add_message(self, role: str, content: str):
        """Append a message to conversation history.
        
        Args:
            role:    'system', 'user', or 'assistant'
            content: Message text
        """
        self.history.append({"role": role, "content": content})


    def get_history(self) -> list:
        """Return full conversation history for passing to Groq API.
        
        Returns:
            List of dicts with 'role' and 'content' keys
        """
        return self.history


    def clear_history(self):
        """Reset conversation history but preserve system prompt.
        
        Keeps the first message if it is a system prompt so LLM
        does not lose its instructions after a clear.
        """
        if self.history and self.history[0]["role"] == "system":
            self.history = [self.history[0]]
        else:
            self.history = []
        self.state.clear()

    def add_system_prompt(self, filepath: Path = SYSTEM_PROMPT_FILEPATH):
        """Read system prompt from markdown file, inject dynamic values, add to history.
        
        Args:
            filepath: Path to system_prompt.md file
            
        Raises:
            FileNotFoundError: If prompt file does not exist
            KeyError: If a placeholder in the prompt file is missing a value
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                prompt = f.read()

            today = datetime.now().strftime("%Y-%m-%d")
            current_month = datetime.now().strftime("%Y-%m")

            filled_prompt = prompt.format(
                username=self.username,
                user_id=self.user_id,
                today=today,
                current_month=current_month
            )

            self.add_message("system", filled_prompt)

        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt file not found at {filepath}")
        except KeyError as e:
            raise KeyError(f"Missing placeholder in system prompt: {e}")


    @property
    def message_count(self) -> int:
        """Return total number of messages in history."""
        return len(self.history)


    def get_last_message(self) -> dict | None:
        """Return the last message in history, or None if history is empty.
        
        Returns:
            Dict with 'role' and 'content', or None
        """
        return self.history[-1] if self.history else None


    def add_assistant_message(self, message):
        """Append assistant message with tool_calls to history in Groq format."""
        tool_calls = message.tool_calls or []
        self.history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in tool_calls
            ]
        })


    def add_tool_result(self, tool_call_id: str, name: str, content: str):
        """Append tool result to history in Groq-required format.
        
        Args:
            tool_call_id: Must match id from assistant tool_calls
            name:         Tool name that was called
            content:      Result string from tool execution
        """
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })


    def trim_old_tool_results(self):
        """Replace old tool result content with summary to save tokens.
        
        Keeps last 4 tool results full, summarizes older ones.
        """
        tool_indices = [i for i, m in enumerate(self.history) if m.get("role") == "tool"]
        
        # keep last 4 tool results intact
        to_trim = tool_indices[:-4] if len(tool_indices) > 4 else []
        
        for i in to_trim:
            content = self.history[i].get("content", "")
            # keep only first 60 chars — enough for context
            if len(content) > 60:
                self.history[i]["content"] = content[:60] + "... [trimmed]"


