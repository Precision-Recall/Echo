"""
Task Router - Semantic Intent Classification.

Uses Gemini Flash to intelligently classify tasks as SIMPLE or COMPLEX,
replacing brittle keyword heuristics with semantic understanding.
"""

from enum import Enum
from typing import Optional
import json
from google import genai
from google.genai import types

class TaskComplexity(Enum):
    """Classification of task complexity."""
    SIMPLE = "simple"
    COMPLEX = "complex"


class TaskRouter:
    """
    Routes tasks using Semantic Analysis via Gemini Flash.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize router with Gemini API key."""
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            
        self._failure_count = 0
        self._max_simple_failures = 2
    
    async def get_routing_strategy(self, transcript: str) -> TaskComplexity:
        """
        Classify task complexity using Gemini Flash.
        
        SIMPLE: Single-step, direct answers, basic tool calls (open app, timer).
        COMPLEX: Multi-step, reasoning required, data retrieval/analysis, file ops.
        """
        if not self.client or not transcript:
            return TaskComplexity.SIMPLE
            
        try:
            prompt = f"""
            Classify the following user request as either 'simple' or 'complex'.
            
            DEFINITIONS:
            - simple: Direct questions ("what time is it"), single-step actions ("open notepad"), basic greetings.
            - complex: Requests requiring multiple steps, data retrieval ("read my emails"), file manipulation ("organize downloads"), analysis, or chaining multiple tools.
            
            REQUEST: "{transcript}"
            
            Return JSON: {{"complexity": "simple" | "complex", "reason": "short explanation"}}
            """
            
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            data = json.loads(response.text)
            complexity = data.get("complexity", "simple").lower()
            
            # log the decision (could use a logger if passed in, but print is fine for now)
            print(f"[Router] '{transcript}' -> {complexity.upper()} ({data.get('reason')})")
            
            if complexity == "complex":
                return TaskComplexity.COMPLEX
            return TaskComplexity.SIMPLE
            
        except Exception as e:
            print(f"[Router] Classification failed, defaulting to SIMPLE: {e}")
            return TaskComplexity.SIMPLE

    def should_escalate(self, transcript: str, error: Optional[Exception] = None) -> bool:
        """
        Determine if we should escalate to multi-agent graph on failure.
        """
        # Always escalate on explicit errors
        if error:
            self._failure_count += 1
            print(f"[Router] Error detected, failure count: {self._failure_count}")
            return True
        
        # Escalate if simple path is repeatedly failing
        if self._failure_count >= self._max_simple_failures:
            print(f"[Router] Failure limit reached ({self._failure_count}), escalating.")
            return True
        
        return False
    
    def reset_failure_count(self):
        """Reset failure counter after successful execution."""
        self._failure_count = 0

