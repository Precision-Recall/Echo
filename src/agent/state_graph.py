"""
LangGraph StateGraph Implementation
Multi-agent system with Voice, Planner, and Executor agents.
"""

from typing import Literal, Callable
from langgraph.graph import StateGraph, END

from .schemas import (
    AgentState, AgentStateType, 
    create_initial_state, has_valid_input, has_valid_plan,
    is_plan_complete, can_retry, has_error
)
from .thinking_logger import ThinkingLogger
from .planner_agent import PlannerAgent
from .executor_agent import ExecutorAgent
from .voice_agent import VoiceAgent


# ============================================================================
# Edge Condition Functions
# ============================================================================

def route_from_listening(state: AgentState) -> Literal["planning", "responding"]:
    """Route from LISTENING state"""
    if has_valid_input(state):
        return "planning"
    # No input - stay in loop or prompt
    return "responding"


def route_from_planning(state: AgentState) -> Literal["executing", "responding"]:
    """Route from PLANNING state"""
    if has_valid_plan(state):
        return "executing"
    # Planning failed - respond with error
    return "responding"


def route_from_executing(
    state: AgentState
) -> Literal["executing", "replanning", "responding"]:
    """Route from EXECUTING state"""
    # Check for errors first
    if has_error(state):
        return "replanning"
    
    # Check if plan complete
    if is_plan_complete(state):
        return "responding"
    
    # More steps to execute
    return "executing"


def route_from_replanning(state: AgentState) -> Literal["executing", "responding"]:
    """Route from REPLANNING state"""
    if can_retry(state, max_retries=3) and has_valid_plan(state):
        return "executing"
    # Max retries or replan failed
    return "responding"


def route_from_responding(state: AgentState) -> Literal["listening", "__end__"]:
    """Route from RESPONDING state"""
    if state.get("should_continue", True):
        return "listening"
    return "__end__"


# ============================================================================
# Graph Builder
# ============================================================================

class MultiAgentGraph:
    """
    LangGraph StateGraph for multi-agent voice assistant.
    
    States:
      - LISTENING: Voice input capture
      - PLANNING: Convert intent to execution plan
      - EXECUTING: Run tools step-by-step
      - REPLANNING: Error recovery with retry logic
      - RESPONDING: TTS output delivery
    """
    
    def __init__(
        self,
        api_key: str,
        mcp_client,
        logger: ThinkingLogger,
        model_name: str = "gemini-2.5-flash"
    ):
        self.logger = logger
        
        # Initialize agents
        self.voice_agent = VoiceAgent(logger)
        self.planner_agent = PlannerAgent(api_key, logger, model_name)
        self.executor_agent = ExecutorAgent(mcp_client, logger)
        
        # Build graph
        self.graph = self._build_graph()
        self.compiled_graph = None
    
    def _build_graph(self) -> StateGraph:
        """Build the StateGraph with nodes and edges"""
        
        # Create graph with state schema
        graph = StateGraph(AgentState)
        
        # ===== Add Nodes =====
        graph.add_node("listening", self.voice_agent.voice_input_node)
        graph.add_node("planning", self.planner_agent.generate_plan)
        graph.add_node("executing", self.executor_agent.execute_step)
        graph.add_node("replanning", self.planner_agent.replan)
        graph.add_node("responding", self.voice_agent.voice_output_node)
        
        # ===== Add Edges =====
        
        # Set entry point
        graph.set_entry_point("listening")
        
        # Conditional edges from LISTENING
        graph.add_conditional_edges(
            "listening",
            route_from_listening,
            {
                "planning": "planning",
                "responding": "responding"
            }
        )
        
        # Conditional edges from PLANNING
        graph.add_conditional_edges(
            "planning",
            route_from_planning,
            {
                "executing": "executing",
                "responding": "responding"
            }
        )
        
        # Conditional edges from EXECUTING (self-loop possible)
        graph.add_conditional_edges(
            "executing",
            route_from_executing,
            {
                "executing": "executing",
                "replanning": "replanning",
                "responding": "responding"
            }
        )
        
        # Conditional edges from REPLANNING
        graph.add_conditional_edges(
            "replanning",
            route_from_replanning,
            {
                "executing": "executing",
                "responding": "responding"
            }
        )
        
        # Conditional edges from RESPONDING (loop or end)
        graph.add_conditional_edges(
            "responding",
            route_from_responding,
            {
                "listening": "listening",
                "__end__": END
            }
        )
        
        return graph
    
    def compile(self):
        """Compile the graph for execution"""
        self.compiled_graph = self.graph.compile()
        return self.compiled_graph
    
    async def run(self, user_input: str, trace_id: str = "", should_continue: bool = True) -> AgentState:
        """
        Run a single interaction through the graph.
        
        Args:
            user_input: Text input from user (or STT transcript)
            trace_id: Optional trace ID for observability
            should_continue: If False, graph exits after responding (one-shot)
            
        Returns:
            Final state after graph execution
        """
        if not self.compiled_graph:
            self.compile()
        
        # Initialize state
        initial_state = create_initial_state(trace_id)
        initial_state["user_input"] = user_input
        initial_state["should_continue"] = should_continue
        
        # Run graph
        self.logger.log_thought(f" Starting graph execution [{initial_state['trace_id']}]")
        
        try:
            final_state = await self.compiled_graph.ainvoke(initial_state)
            self.logger.log_thought(f"✅ Graph complete [{initial_state['trace_id']}]")
            return final_state
            
        except Exception as e:
            self.logger.log_error(f"Graph error: {e}")
            initial_state["error_context"] = {
                "failed_step_id": "graph",
                "error_message": str(e),
                "error_type": type(e).__name__,
                "recoverable": False
            }
            initial_state["response_text"] = f"An error occurred: {e}"
            return initial_state
    
    async def run_for_voice(self, transcript: str) -> str:
        """
        Run multi-agent graph for a voice transcript.
        
        This is the entry point for complex task routing from GeminiLiveClient.
        
        Args:
            transcript: User's voice transcript
            
        Returns:
            Response text to speak back to user
        """
        self.logger.log_thought(f"🧠 Multi-agent processing: {transcript[:50]}...")
        
        final_state = await self.run(transcript, should_continue=False)
        
        response = final_state.get("response_text", "Task completed.")
        self.logger.log_thought(f"✅ Multi-agent response: {response[:80]}...")
        
        return response
    
    async def run_continuous(
        self, 
        input_callback: Callable[[], str],
        output_callback: Callable[[str], None],
        should_continue: Callable[[], bool]
    ):
        """
        Run continuous voice loop.
        
        Args:
            input_callback: Async function that returns user input
            output_callback: Async function to deliver response
            should_continue: Function that returns False to stop loop
        """
        if not self.compiled_graph:
            self.compile()
        
        self.logger.log_thought(" Starting continuous voice loop")
        
        while should_continue():
            try:
                # Get input
                user_input = input_callback()
                if not user_input:
                    continue
                
                # Run graph
                state = await self.run(user_input)
                
                # Deliver response
                response = state.get("response_text", "")
                if response:
                    output_callback(response)
                    
            except Exception as e:
                self.logger.log_error(f"Loop error: {e}")
                output_callback(f"An error occurred: {e}")


# ============================================================================
# Factory Function
# ============================================================================

async def create_multi_agent_graph(
    api_key: str,
    mcp_url: str = "http://localhost:8000/mcp",
    logger: ThinkingLogger = None,
    model_name: str = "gemini-2.5-flash"
) -> MultiAgentGraph:
    """
    Factory function to create and initialize the multi-agent graph.
    
    Args:
        api_key: Gemini API key
        mcp_url: Windows-MCP server URL
        logger: Optional ThinkingLogger instance
        model_name: Gemini model to use
        
    Returns:
        Initialized MultiAgentGraph ready for execution
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient
    
    if logger is None:
        logger = ThinkingLogger()
    
    # Connect to MCP
    logger.log_thought("🔌 Connecting to Windows-MCP...")
    
    mcp_client = MultiServerMCPClient({
        "windows-mcp": {
            "transport": "http",
            "url": mcp_url,
        }
    })
    
    # Create graph
    graph = MultiAgentGraph(
        api_key=api_key,
        mcp_client=mcp_client,
        logger=logger,
        model_name=model_name
    )
    
    # Initialize executor
    await graph.executor_agent.initialize()
    
    # Compile graph
    graph.compile()
    
    logger.log_thought("✅ Multi-agent graph ready")
    
    return graph
