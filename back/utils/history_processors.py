"""
History processors for PydanticAI agents.
Handles message summarization to manage token limits.
"""

from typing import List

import tiktoken
from pydantic_ai import Agent, ModelMessage
from pydantic_ai.messages import (ModelResponse, SystemPromptPart, TextPart,
                                  UserPromptPart)

from back.config import get_llm_config

# Initialize tokenizer (using cl100k_base which is standard for GPT-4/3.5/DeepSeek)
try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    # Fallback if encoding not found
    tokenizer = tiktoken.get_encoding("gpt2")

def count_tokens(text: str) -> int:
    """
    Count tokens in a text string.
    """
    return len(tokenizer.encode(text))

def estimate_history_tokens(messages: List[ModelMessage]) -> int:
    """
    Estimate total tokens in a message history.
    Iterates through parts of each message.
    """
    total = 0
    for msg in messages:
        if hasattr(msg, 'parts'):
            for part in msg.parts:
                if hasattr(part, 'content') and isinstance(part.content, str):
                    total += count_tokens(part.content)
    return total

async def summarize_old_messages(messages: List[ModelMessage]) -> List[ModelMessage]:
    """
    Summarize old messages if the total token count exceeds the configured limit.
    
    Strategy:
    1. Check if token count > limit.
    2. If yes, keep the last N messages (configured).
    3. Keep the system prompt (assumed to be the first message if present).
    4. Summarize the messages in between.
    5. Return [SystemPrompt, SummaryMessage, ...RecentMessages].
    """
    llm_config = get_llm_config()
    token_limit = llm_config.token_limit
    keep_last_n = llm_config.keep_last_n_messages

    current_tokens = estimate_history_tokens(messages)
    
    if current_tokens <= token_limit:
        return messages

    # Identify and extract System Prompts from ANY message
    # We want to preserve ALL system prompts, regardless of where they are.
    system_parts: List[SystemPromptPart] = []
    clean_messages: List[ModelMessage] = []

    from pydantic_ai.messages import ModelRequest, ModelResponse

    for msg in messages:
        if hasattr(msg, 'parts'):
            new_parts = []
            has_system = False
            for part in msg.parts:
                if isinstance(part, SystemPromptPart):
                    system_parts.append(part)
                    has_system = True
                else:
                    new_parts.append(part)
            
            # If we found system parts, we might need to restructure the message
            if has_system:
                if new_parts:
                    # Message had mixed content. Reconstruct it without system parts.
                    # We assume it matches the original type if possible, or default to ModelRequest for User inputs
                    # simplified: just check type
                    if isinstance(msg, ModelResponse):
                         clean_messages.append(ModelResponse(parts=new_parts))
                    else:
                         # Default to ModelRequest for anything else (likely User or Tool)
                         clean_messages.append(ModelRequest(parts=new_parts))
                else:
                    # Message was ONLY system parts. It is fully extracted to system_parts.
                    pass
            else:
                # No system parts, keep message as is
                clean_messages.append(msg)
        else:
            # Message has no parts attribute (rare in this context but possible), keep it
            clean_messages.append(msg)

    # If we have fewer clean messages than the keep limit, we can't summarize much 
    # (except maybe if the system prompt was huge, but we are keeping system prompt anyway).
    if len(clean_messages) <= keep_last_n:
        # Reconstruct with system prompt at start
        if system_parts:
            # Combine all system parts into one ModelRequest or separate?
            # Usually one message with multiple parts is fine.
            return [ModelRequest(parts=system_parts)] + clean_messages
        return clean_messages

    # Summarization Logic
    # Messages to summarize: from start up to (total - keep_last_n)
    end_index = len(clean_messages) - keep_last_n
    
    msgs_to_summarize = clean_messages[:end_index]
    recent_messages = clean_messages[end_index:]

    if not msgs_to_summarize:
        if system_parts:
            return [ModelRequest(parts=system_parts)] + recent_messages
        return recent_messages

    # Create a temporary agent for summarization
    # We use a lightweight prompt
    summarizer_agent = Agent(
        model=llm_config.model, # Use same model for now
        system_prompt="You are a helpful assistant that summarizes conversation history.",
    )

    # Format messages for the summarizer
    transcript = ""
    for msg in msgs_to_summarize:
        transcript += f"{msg}\n"

    summary_prompt = (
        "Please summarize the following conversation history into a single concise paragraph. "
        "Retain key information, decisions, and current state. "
        "Ignore specific tool call details unless they changed the state significantly.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    try:
        result = await summarizer_agent.run(summary_prompt)
        summary_text = result.data
    except Exception as e:
        # Fallback if summarization fails
        summary_text = f"[Error during summarization: {e}. Previous context omitted.]"

    summary_message = ModelResponse(
        parts=[TextPart(content=f"**SYSTEM SUMMARY OF PAST EVENTS**:\n{summary_text}")]
    )

    new_history = []
    
    # Prepend preserved system parts
    if system_parts:
        new_history.append(ModelRequest(parts=system_parts))
    
    new_history.append(summary_message)
    new_history.extend(recent_messages)

    return new_history
