"""
Short-term memory management for conversations.
Stores conversation history per thread_id with automatic trimming and summarization.
"""
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ConversationMessage:
    role: str  # 'user' or 'model'
    content: str
    timestamp: float
    tool_calls: Optional[List[dict]] = None


class MemoryManager:
    """
    In-memory conversation storage with automatic trimming.
    In production, replace with Redis, PostgreSQL, or other persistent storage.
    """
    
    def __init__(self, max_messages: int = 20, max_tokens_estimate: int = 4000):
        """
        Args:
            max_messages: Maximum number of messages to keep in memory
            max_tokens_estimate: Rough estimate of max tokens (4 chars ≈ 1 token)
        """
        self.conversations: Dict[str, List[ConversationMessage]] = {}
        self.max_messages = max_messages
        self.max_tokens_estimate = max_tokens_estimate
    
    def add_message(self, thread_id: str, role: str, content: str, tool_calls: Optional[List[dict]] = None):
        """Add a message to the conversation history."""
        if thread_id not in self.conversations:
            self.conversations[thread_id] = []
        
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().timestamp(),
            tool_calls=tool_calls
        )
        
        self.conversations[thread_id].append(message)
        
        # Auto-trim if needed
        self._trim_if_needed(thread_id)
    
    def get_history(self, thread_id: str, last_n: Optional[int] = None) -> List[ConversationMessage]:
        """Get conversation history for a thread."""
        if thread_id not in self.conversations:
            return []
        
        messages = self.conversations[thread_id]
        if last_n:
            return messages[-last_n:]
        return messages
    
    def get_context_string(self, thread_id: str) -> str:
        """Get conversation history as a formatted string for context."""
        messages = self.get_history(thread_id)
        
        context_parts = []
        for msg in messages:
            prefix = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{prefix}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def clear_thread(self, thread_id: str):
        """Clear all messages for a thread."""
        if thread_id in self.conversations:
            del self.conversations[thread_id]
    
    def _trim_if_needed(self, thread_id: str):
        """Trim old messages if exceeding limits."""
        messages = self.conversations[thread_id]
        
        # Trim by message count
        if len(messages) > self.max_messages:
            # Keep first message (often contains important context) and recent messages
            self.conversations[thread_id] = [messages[0]] + messages[-(self.max_messages-1):]
        
        # Trim by estimated token count
        total_chars = sum(len(msg.content) for msg in self.conversations[thread_id])
        estimated_tokens = total_chars // 4
        
        if estimated_tokens > self.max_tokens_estimate:
            # Remove oldest messages until under limit
            while estimated_tokens > self.max_tokens_estimate and len(self.conversations[thread_id]) > 2:
                removed = self.conversations[thread_id].pop(1)  # Keep first, remove second oldest
                estimated_tokens -= len(removed.content) // 4
    
    def get_stats(self, thread_id: str) -> dict:
        """Get statistics about a conversation thread."""
        if thread_id not in self.conversations:
            return {"message_count": 0, "estimated_tokens": 0}
        
        messages = self.conversations[thread_id]
        total_chars = sum(len(msg.content) for msg in messages)
        
        return {
            "message_count": len(messages),
            "estimated_tokens": total_chars // 4,
            "total_characters": total_chars
        }


# Global memory manager instance
memory_manager = MemoryManager()

