"""AgentCore — main LLM loop for Finance Agent.

Handles Groq API calls, tool call dispatch, and multi-turn tool execution.
Supports multiple tool calls per turn with a max limit to prevent infinite loops.
"""

import os
import json
from groq import Groq, BadRequestError
from dotenv import load_dotenv
from tools import registry

load_dotenv()

MAX_TOOL_CALLS = 5
MODEL = "openai/gpt-oss-120b"  # for development
# MODEL = "llama-3.3-70b-versatile"  # for production

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def run(user_message: str, session) -> str:
    """Process a user message through the LLM loop.

    Sends message to Groq, handles tool calls, returns final response.

    Args:
        user_message: Raw message from user
        session:      Current Session instance

    Returns:
        Final natural language response string from LLM
    """

    # Trim tool result from history
    session.trim_old_tool_results()

    if session.message_count > 20:
        session.clear_history()
        session.add_message("system", "History cleared to save context. Continue normally.")

    session.add_message("user", user_message)

    tool_call_count = 0
    errors = []

    while tool_call_count < MAX_TOOL_CALLS:

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=session.get_history(),
                tools=registry.get_schemas(),
                tool_choice="none" if tool_call_count > 0 else "auto",
                parallel_tool_calls=False
            )
        except BadRequestError as e:
            error_str = str(e)
            if "tool_use_failed" in error_str:
                # silent retry once — clears model confusion
                try:
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=session.get_history(),
                        tools=registry.get_schemas(),
                        tool_choice="auto",
                        parallel_tool_calls=False
                    )
                    message = response.choices[0].message
                    if not message.tool_calls:
                        final_response = message.content or "Done."
                        session.add_message("assistant", final_response)
                        return final_response
                    session.add_assistant_message(message)
                    for tool_call in message.tool_calls:
                        tool_call_count += 1
                        try:
                            args = json.loads(tool_call.function.arguments)
                            result = registry.execute(tool_call.function.name, args, session)
                        except Exception as ex:
                            result = f"Tool failed: {str(ex)}"
                        session.add_tool_result(tool_call.id, tool_call.function.name, result)
                    continue  # go back to top of while loop for final response
                except Exception:
                    return "I had trouble with that — could you try saying 'yes delete it' or 'confirm delete'?"
            return f"Request failed: {error_str}"

        message = response.choices[0].message

        # no tool call — LLM gave final response
        if not message.tool_calls:
            final_response = message.content or "I couldn't generate a response."
            session.add_message("assistant", final_response)
            return final_response

        # append assistant message with tool calls to history
        session.add_assistant_message(message)

        # handle all tool calls in this turn
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_call_count += 1

            try:
                args = json.loads(tool_call.function.arguments)
                result = registry.execute(tool_name, args, session)
            except Exception as e:
                result = f"Tool {tool_name} failed: {str(e)}"
                errors.append(f"{tool_name}: {str(e)}")

            session.add_tool_result(tool_call.id, tool_call.function.name, result)

        # max tool calls reached — force final response
        if tool_call_count >= MAX_TOOL_CALLS:
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=session.get_history(),
                    tools=registry.get_schemas(),
                    tool_choice="none"
                )
                final_response = response.choices[0].message.content or "Done."
            except Exception:
                final_response = "I've completed the operations but couldn't generate a summary."

            session.add_message("assistant", final_response)
            return final_response


    return "Something went wrong — please try again"