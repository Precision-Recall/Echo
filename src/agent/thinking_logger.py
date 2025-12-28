"""
Thinking Logger for Agent Reasoning Trace
Captures and streams agent thoughts, actions, and observations
"""

from datetime import datetime
from typing import Dict, Any, List, AsyncIterator
from enum import Enum
import asyncio
import json


class EventType(Enum):
    """Types of thinking events"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    ERROR = "error"
    RESULT = "result"


class ThinkingLogger:
    """Logger for agent thinking trace"""
    
    def __init__(self):
        """Initialize thinking logger"""
        self.events: List[Dict[str, Any]] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
    def _create_event(self, event_type: EventType, content: Any, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a thinking event
        
        Args:
            event_type: Type of event
            content: Event content
            metadata: Additional metadata
            
        Returns:
            Event dictionary
        """
        event = {
            "type": event_type.value,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        return event
    
    def log_thought(self, message: str, metadata: Dict[str, Any] = None) -> None:
        """
        Log an agent thought
        
        Args:
            message: Thought message
            metadata: Additional metadata
        """
        event = self._create_event(EventType.THOUGHT, message, metadata)
        self.events.append(event)
        # Non-blocking queue put
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
        
        print(f"💭 {message}")
    
    def log_action(self, tool_name: str, params: Dict[str, Any], metadata: Dict[str, Any] = None) -> None:
        """
        Log an agent action
        
        Args:
            tool_name: Name of the tool being called
            params: Tool parameters
            metadata: Additional metadata
        """
        content = {
            "tool": tool_name,
            "parameters": params
        }
        event = self._create_event(EventType.ACTION, content, metadata)
        self.events.append(event)
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
        
        print(f"🔧 Action: {tool_name}({json.dumps(params, indent=2)})")
    
    def log_observation(self, result: Any, metadata: Dict[str, Any] = None) -> None:
        """
        Log an observation (result of an action)
        
        Args:
            result: Action result
            metadata: Additional metadata
        """
        event = self._create_event(EventType.OBSERVATION, result, metadata)
        self.events.append(event)
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
        
        # Print summary of observation
        if isinstance(result, dict) and "success" in result:
            status = "✓" if result.get("success") else "✗"
            message = result.get("message", result.get("error", "No message"))
            print(f"👁️ {status} {message}")
        else:
            print(f"👁️ Observation: {str(result)[:100]}")
    
    def log_error(self, error_message: str, metadata: Dict[str, Any] = None) -> None:
        """
        Log an error
        
        Args:
            error_message: Error message
            metadata: Additional metadata
        """
        event = self._create_event(EventType.ERROR, error_message, metadata)
        self.events.append(event)
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
        
        print(f"❌ Error: {error_message}")
    
    def log_result(self, result: Any, metadata: Dict[str, Any] = None) -> None:
        """
        Log final result
        
        Args:
            result: Final result
            metadata: Additional metadata
        """
        event = self._create_event(EventType.RESULT, result, metadata)
        self.events.append(event)
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
        
        print(f"✅ Result: {result}")
    
    def get_full_trace(self) -> List[Dict[str, Any]]:
        """
        Get complete thinking trace
        
        Returns:
            List of all events
        """
        return self.events.copy()
    
    async def stream_events(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream thinking events in real-time
        
        Yields:
            Thinking events as they occur
        """
        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                # Check if there are any events in the list that weren't yielded
                continue
            except Exception as e:
                print(f"Error streaming event: {e}")
                break
    
    def clear(self) -> None:
        """Clear all events"""
        self.events.clear()
        # Clear queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def to_json(self) -> str:
        """
        Export trace as JSON
        
        Returns:
            JSON string of all events
        """
        return json.dumps(self.events, indent=2)
    
    def save_to_file(self, filename: str) -> None:
        """
        Save thinking trace to file
        
        Args:
            filename: Output filename
        """
        with open(filename, 'w') as f:
            f.write(self.to_json())
        print(f"📝 Saved thinking trace to {filename}")


# Example usage
if __name__ == "__main__":
    logger = ThinkingLogger()
    
    logger.log_thought("Need to open Notepad to write a note")
    logger.log_action("launch_application", {"app_name": "notepad"})
    logger.log_observation({"success": True, "message": "Notepad launched"})
    logger.log_thought("Now typing the text")
    logger.log_action("type_text_input", {"text": "Hello World!"})
    logger.log_observation({"success": True, "message": "Text typed"})
    logger.log_result("Successfully created note in Notepad")
    
    print("\n📋 Full trace:")
    print(logger.to_json())
