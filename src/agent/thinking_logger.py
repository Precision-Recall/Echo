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


from src.utils.ui import print_thought, print_action, print_observation, print_error, print_result

class ThinkingLogger:
    """Logger for agent thinking trace"""
    
    # Bug 15: Cap events at a rolling window to prevent unbounded memory growth
    MAX_EVENTS = 1000
    
    def __init__(self, ui_callback=None):
        """Initialize thinking logger"""
        self.events: List[Dict[str, Any]] = []
        # Bug 9: Lazy queue creation -- initialized to None, created on first use
        # inside a running event loop to avoid "attached to a different loop" errors
        self.event_queue: asyncio.Queue = None
        self.ui_callback = ui_callback
    
    def _ensure_queue(self):
        """Bug 9: Lazily create the asyncio.Queue on first use.
        
        All log_* callers run inside asyncio.run(), so a running loop
        always exists at the point of first use.
        """
        if self.event_queue is None:
            self.event_queue = asyncio.Queue()
        
    def _create_event(self, event_type: EventType, content: Any, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a thinking event"""
        event = {
            "type": event_type.value,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        return event
    
    def _append_event(self, event: Dict[str, Any]) -> None:
        """Bug 15: Append event and trim to rolling window.
        
        Single point of change for the cap -- all log_* methods call this
        instead of directly appending + trimming in 5 places.
        """
        self.events.append(event)
        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]
        
        self._ensure_queue()
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
    
    def log_thought(self, message: str, metadata: Dict[str, Any] = None) -> None:
        """Log an agent thought"""
        event = self._create_event(EventType.THOUGHT, message, metadata)
        self._append_event(event)
        
        if self.ui_callback:
            self.ui_callback("thought", message)
        else:
            print_thought(message)
    
    def log_action(self, tool_name: str, params: Dict[str, Any], metadata: Dict[str, Any] = None) -> None:
        """Log an agent action"""
        content = {
            "tool": tool_name,
            "parameters": params
        }
        event = self._create_event(EventType.ACTION, content, metadata)
        self._append_event(event)
        
        if self.ui_callback:
            self.ui_callback("action", f"{tool_name}({json.dumps(params, indent=None)})")
        else:
            print_action(tool_name, json.dumps(params, indent=None))
    
    def log_observation(self, result: Any, metadata: Dict[str, Any] = None) -> None:
        """Log an observation"""
        event = self._create_event(EventType.OBSERVATION, result, metadata)
        self._append_event(event)
        
        # Prepare message
        if isinstance(result, dict) and "success" in result:
            success = result.get("success", False)
            message = result.get("message", result.get("error", "No message"))
        else:
            message = str(result)[:100]
            success = True
            
        if self.ui_callback:
            status = "+" if success else "x"
            self.ui_callback("observation", f"{status} {message}")
        else:
            print_observation(message, success)
    
    def log_error(self, error_message: str, metadata: Dict[str, Any] = None) -> None:
        """Log an error"""
        event = self._create_event(EventType.ERROR, error_message, metadata)
        self._append_event(event)
        
        if self.ui_callback:
            self.ui_callback("error", error_message)
        else:
            print_error(error_message)
    
    def log_result(self, result: Any, metadata: Dict[str, Any] = None) -> None:
        """Log final result"""
        event = self._create_event(EventType.RESULT, result, metadata)
        self._append_event(event)
        
        if self.ui_callback:
            self.ui_callback("result", str(result))
        else:
            from src.utils.ui import console
            console.print(f"[bold green]Result:[/bold green] {result}")
    
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
        self._ensure_queue()
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
        if self.event_queue is not None:
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
        print(f"Saved thinking trace to {filename}")


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
    
    print("\nFull trace:")
    print(logger.to_json())
