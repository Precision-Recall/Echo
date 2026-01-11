"""
Planner Agent - Converts user intent into structured ExecutionPlan
"""

import json
import uuid
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from .schemas import (
    AgentState, ExecutionPlan, ExecutionStep, 
    AgentStateType
)
from .thinking_logger import ThinkingLogger


PLANNER_SYSTEM_PROMPT = """You are a Windows desktop automation planner.

Your job is to convert user requests into structured execution plans.

Available tools:
- App-Tool: Launch/switch applications (mode: "launch" | "switch", name: app_name)
- Powershell-Tool: Execute PowerShell commands (command: string)
- State-Tool: Get current desktop state (no params)
- Click-Tool: Click at coordinates (x: int, y: int, button: "left"|"right")
- Type-Tool: Type text at screen location (loc: [x,y] REQUIRED, text: string) - use Shortcut for simple input
- Scroll-Tool: Scroll (direction: "up"|"down", amount: int)
- Shortcut-Tool: Press keyboard shortcut (shortcut: string like "ctrl+c")
- Wait-Tool: Wait for duration (duration: float in seconds)

Timeout guidelines (in seconds):
- App-Tool: 30 (GUI apps take time to launch)
- Powershell-Tool: 45 (commands may take time)
- Click/Type/Scroll/Shortcut: 10 (quick operations)
- State-Tool: 15 (screen capture)
- Wait-Tool: duration + 5

Output a JSON execution plan with this structure:
{
  "user_intent": "Brief description of what user wants",
  "steps": [
    {
      "step_id": "step_1",
      "tool_name": "App-Tool",
      "parameters": {"mode": "launch", "name": "Notepad"},
      "description": "Launch Notepad application",
      "depends_on": [],
      "timeout_seconds": 30
    }
  ],
  "requires_confirmation": false
}

Rules:
1. Always use State-Tool first if you need to know current state
2. Use Wait-Tool after launching apps (1-2 seconds)
3. Break complex tasks into atomic steps
4. Each step should have clear dependencies
5. Set requires_confirmation=true for destructive actions
6. PREFER Powershell-Tool over App-Tool when possible (faster, more reliable)
7. HANDLE MIXED LANGUAGE: If input contains foreign characters (e.g. Hindi, Chinese) alongside an app name (like 'YouTube', 'Chrome'), assume the user wants to SEARCH or OPEN specific content. Do NOT just open the app.
   - Example: "αñ▓αñ░ αñçαñ¿ YouTube" -> Launch Chrome -> Search YouTube for the phonetic string or closest guess.
   - If exact intent is unclear but platform is known, Open App -> Focus Search Bar -> Type the raw input.

ONLY output valid JSON. No explanation or markdown."""


ERROR_RESPONSE_PROMPT = """Generate a brief, friendly response explaining you couldn't complete the task.
Context: {context}
Error: {error}

Be conversational, concise (1-2 sentences), and suggest what the user might try instead.
Output ONLY the response text, no formatting."""

# Fallback for when there's literally no input to process
EMPTY_INPUT_FALLBACK = "I didn't catch that. Could you repeat?"


class PlannerAgent:
    """Generates structured execution plans from user intent"""
    
    def __init__(
        self,
        api_key: str,
        logger: ThinkingLogger,
        model_name: str = "gemini-2.5-flash"
    ):
        self.logger = logger
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.1,  # Low temp for deterministic plans
        )
    
    async def _generate_error_response(self, context: str, error: str) -> str:
        """Generate a natural error response using LLM"""
        try:
            prompt = ERROR_RESPONSE_PROMPT.format(context=context, error=error)
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception:
            # Fallback if LLM call fails
            return f"Sorry, I ran into an issue: {error}"
    
    async def generate_plan(self, state: AgentState) -> AgentState:
        """
        Node function: Generate execution plan from user input.
        
        Args:
            state: Current agent state with user_input
            
        Returns:
            Updated state with plan field populated
        """
        user_input = state.get("user_input", "")
        
        if not user_input.strip():
            self.logger.log_error("No user input provided for planning")
            state["error_context"] = {
                "failed_step_id": "planning",
                "error_message": "No user input provided",
                "error_type": "InvalidInput",
                "recoverable": False
            }
            state["current_state"] = AgentStateType.RESPONDING
            state["response_text"] = EMPTY_INPUT_FALLBACK
            return state
        
        self.logger.log_thought(f" Planning: {user_input}")
        
        try:
            # Call LLM for plan generation
            messages = [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=f"User request: {user_input}")
            ]
            
            response = await self.llm.ainvoke(messages)
            raw_plan = response.content
            
            # Parse JSON plan
            plan_dict = self._parse_plan(raw_plan)
            
            if plan_dict:
                # Enrich with metadata
                plan_dict["plan_id"] = f"plan_{uuid.uuid4().hex[:8]}"
                
                self.logger.log_thought(f"Generated {len(plan_dict.get('steps', []))} steps")
                
                state["plan"] = plan_dict
                state["current_step_index"] = 0
                state["current_state"] = AgentStateType.EXECUTING
            else:
                raise ValueError("Failed to parse plan from LLM response")
                
        except Exception as e:
            self.logger.log_error(f"Planning error: {e}")
            state["error_context"] = {
                "failed_step_id": "planning",
                "error_message": str(e),
                "error_type": type(e).__name__,
                "recoverable": True
            }
            state["current_state"] = AgentStateType.RESPONDING
            # Use LLM for contextual error response
            state["response_text"] = await self._generate_error_response(
                context=user_input,
                error=str(e)
            )
        
        return state
    
    def _parse_plan(self, raw: str) -> Optional[dict]:
        """Parse JSON plan from LLM response"""
        # Clean markdown code blocks if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            self.logger.log_error(f"JSON parse error: {raw[:200]}")
            return None
    
    async def replan(self, state: AgentState) -> AgentState:
        """
        Node function: Generate new plan after error.
        
        Args:
            state: State with error_context and original plan
            
        Returns:
            Updated state with modified plan or error response
        """
        error_ctx = state.get("error_context", {})
        original_plan = state.get("plan", {})
        retry_count = state.get("retry_count", 0)
        
        self.logger.log_thought(f"🔄 Replanning (attempt {retry_count + 1}/3)")
        
        # Max retries check
        if retry_count >= 3:
            self.logger.log_error("Max retries exceeded")
            state["current_state"] = AgentStateType.RESPONDING
            state["response_text"] = "I tried multiple times but couldn't complete the task. Please try a different approach."
            return state
        
        # Build replan prompt
        replan_context = f"""
Original plan failed. Error details:
- Failed step: {error_ctx.get('failed_step_id')}
- Error: {error_ctx.get('error_message')}
- Error type: {error_ctx.get('error_type')}

Original user intent: {original_plan.get('user_intent', state.get('user_input', ''))}

Previous steps completed: {len(state.get('execution_results', []))}

Please generate a NEW plan that:
1. Accounts for the error
2. Tries an alternative approach
3. Skips already-completed steps if possible
"""
        
        try:
            messages = [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=replan_context)
            ]
            
            response = await self.llm.ainvoke(messages)
            plan_dict = self._parse_plan(response.content)
            
            if plan_dict:
                plan_dict["plan_id"] = f"replan_{uuid.uuid4().hex[:8]}"
                state["plan"] = plan_dict
                state["current_step_index"] = 0
                state["retry_count"] = retry_count + 1
                state["error_context"] = None
                state["current_state"] = AgentStateType.EXECUTING
                
                self.logger.log_thought(f"✅ Replan generated with {len(plan_dict.get('steps', []))} steps")
            else:
                raise ValueError("Failed to generate replan")
                
        except Exception as e:
            self.logger.log_error(f"Replanning failed: {e}")
            state["current_state"] = AgentStateType.RESPONDING
            state["response_text"] = f"I couldn't recover from the error. {error_ctx.get('error_message', '')}"
        
        return state
