"""
Executor Agent - Runs MCP tools based on execution plans
"""

import asyncio
import time
from typing import Dict, Any, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from .schemas import (
    AgentState, StepResult, StepStatus, ErrorContext,
    AgentStateType
)
from .thinking_logger import ThinkingLogger


class ExecutorAgent:
    """Executes tools based on structured plans"""
    
    def __init__(
        self,
        mcp_client: MultiServerMCPClient,
        logger: ThinkingLogger,
        default_timeout: float = 15.0
    ):
        self.mcp_client = mcp_client
        self.logger = logger
        self.default_timeout = default_timeout
        self._tool_map: Dict[str, Any] = {}
    
    async def initialize(self):
        """Load tools from MCP server"""
        tools = await self.mcp_client.get_tools()
        self._tool_map = {t.name: t for t in tools}
        self.logger.log_thought(f"Executor loaded {len(tools)} tools")
    
    async def execute_step(self, state: AgentState) -> AgentState:
        """
        Node function: Execute current step in the plan.
        
        Executes one step at a time, allowing state inspection between steps.
        
        Args:
            state: Current state with plan and current_step_index
            
        Returns:
            Updated state with execution result
        """
        plan = state.get("plan")
        if not plan:
            self.logger.log_error("No plan to execute")
            state["current_state"] = AgentStateType.RESPONDING
            state["response_text"] = "No execution plan available."
            return state
        
        steps = plan.get("steps", [])
        current_idx = state.get("current_step_index", 0)
        
        # Check if all steps done
        if current_idx >= len(steps):
            self.logger.log_thought("✅ All steps completed")
            state["current_state"] = AgentStateType.RESPONDING
            state["response_text"] = self._build_success_response(state)
            return state
        
        step = steps[current_idx]
        step_id = step.get("step_id", f"step_{current_idx}")
        tool_name = step.get("tool_name", "")
        params = step.get("parameters", {})
        timeout = step.get("timeout_seconds", self.default_timeout)
        
        self.logger.log_thought(f"Step {current_idx + 1}/{len(steps)}: {tool_name}")
        self.logger.log_action(tool_name, params)
        
        start_time = time.time()
        
        try:
            # Execute tool with timeout
            result = await self._execute_tool(tool_name, params, timeout)
            duration = time.time() - start_time
            
            # Record success
            step_result = StepResult(
                step_id=step_id,
                status=StepStatus.SUCCESS,
                output=result,
                duration_seconds=duration
            )
            
            execution_results = state.get("execution_results", [])
            execution_results.append(step_result.to_dict())
            state["execution_results"] = execution_results
            
            # Store raw output
            tool_outputs = state.get("tool_outputs", {})
            tool_outputs[step_id] = result
            state["tool_outputs"] = tool_outputs
            
            self.logger.log_observation(f"Result: {str(result)[:200]}")
            
            # Move to next step
            state["current_step_index"] = current_idx + 1
            
            # Stay in EXECUTING state for next step
            state["current_state"] = AgentStateType.EXECUTING
            
        except asyncio.TimeoutError:
            self.logger.log_error(f"Tool timeout after {timeout}s")
            state = self._handle_step_error(
                state, step_id, 
                f"Tool execution timed out after {timeout} seconds",
                "TimeoutError",
                recoverable=True
            )
            
        except Exception as e:
            self.logger.log_error(f"Tool error: {e}")
            state = self._handle_step_error(
                state, step_id,
                str(e),
                type(e).__name__,
                recoverable=True
            )
        
        return state
    
    async def _execute_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any],
        timeout: float
    ) -> Any:
        """Execute a single tool with timeout"""
        if not self._tool_map:
            await self.initialize()
        
        if tool_name not in self._tool_map:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self._tool_map[tool_name]
        
        if hasattr(tool, "ainvoke"):
            result = await asyncio.wait_for(
                tool.ainvoke(params),
                timeout=timeout
            )
        else:
            result = await asyncio.wait_for(
                asyncio.to_thread(tool.invoke, params),
                timeout=timeout
            )
        
        return result
    
    def _handle_step_error(
        self,
        state: AgentState,
        step_id: str,
        error_message: str,
        error_type: str,
        recoverable: bool = True
    ) -> AgentState:
        """Handle step execution error"""
        # Record failed result
        step_result = StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=error_message
        )
        
        execution_results = state.get("execution_results", [])
        execution_results.append(step_result.to_dict())
        state["execution_results"] = execution_results
        
        # Set error context
        state["error_context"] = ErrorContext(
            failed_step_id=step_id,
            error_message=error_message,
            error_type=error_type,
            recoverable=recoverable
        ).to_dict()
        
        # Transition to replanning
        state["current_state"] = AgentStateType.REPLANNING
        
        return state
    
    def _build_success_response(self, state: AgentState) -> str:
        """Build success response text for TTS"""
        plan = state.get("plan", {})
        intent = plan.get("user_intent", "the task")
        results = state.get("execution_results", [])
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        total = len(results)
        
        if success_count == total:
            return f"Done! I completed {intent}."
        else:
            return f"Completed {success_count} of {total} steps for {intent}."
