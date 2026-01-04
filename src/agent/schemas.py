"""
State Schemas for LangGraph Multi-Agent System
Defines TypedDict schemas for state, plans, and execution results.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class AgentStateType(str, Enum):
    """Current state in the StateGraph"""
    LISTENING = "listening"
    PLANNING = "planning"
    EXECUTING = "executing"
    REPLANNING = "replanning"
    RESPONDING = "responding"


class StepStatus(str, Enum):
    """Status of an execution step"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================================
# Execution Plan Schemas
# ============================================================================

@dataclass
class ExecutionStep:
    """Single step in an execution plan"""
    step_id: str
    tool_name: str
    parameters: Dict[str, Any]
    description: str
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "description": self.description,
            "depends_on": self.depends_on,
            "timeout_seconds": self.timeout_seconds
        }


@dataclass
class ExecutionPlan:
    """Structured execution plan from Planner"""
    plan_id: str
    user_intent: str
    steps: List[ExecutionStep]
    estimated_duration_seconds: float = 0.0
    requires_confirmation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "user_intent": self.user_intent,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "requires_confirmation": self.requires_confirmation
        }


# ============================================================================
# Result Schemas
# ============================================================================

@dataclass
class StepResult:
    """Result of executing a single step"""
    step_id: str
    status: StepStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class ErrorContext:
    """Context for error handling and replanning"""
    failed_step_id: str
    error_message: str
    error_type: str
    recoverable: bool
    suggested_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "failed_step_id": self.failed_step_id,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action
        }


# ============================================================================
# Agent State (Main StateGraph State)
# ============================================================================

class AgentState(TypedDict, total=False):
    """
    Main state schema for the multi-agent StateGraph.
    All fields are optional (total=False) for flexibility.
    """
    # Current state
    current_state: AgentStateType
    
    # Voice Input
    user_input: str                         # Raw voice transcript
    audio_data: Optional[bytes]             # Raw audio bytes (for context)
    
    # Planning
    plan: Optional[Dict[str, Any]]          # ExecutionPlan as dict
    current_step_index: int                 # Index of currently executing step
    
    # Execution
    execution_results: List[Dict[str, Any]] # List of StepResult dicts
    tool_outputs: Dict[str, Any]            # Raw tool outputs keyed by step_id
    
    # Error Handling
    error_context: Optional[Dict[str, Any]] # ErrorContext as dict
    retry_count: int                        # Current retry attempt (max 3)
    
    # Response
    response_text: str                      # Text for TTS output
    should_continue: bool                   # Continue listening after response?
    
    # Observability
    trace_id: str                           # Unique ID for this interaction
    timestamps: Dict[str, float]            # State transition timestamps


# ============================================================================
# Initial State Factory
# ============================================================================

def create_initial_state(trace_id: str = "") -> AgentState:
    """Create a fresh initial state for a new interaction"""
    import time
    import uuid
    
    return AgentState(
        current_state=AgentStateType.LISTENING,
        user_input="",
        audio_data=None,
        plan=None,
        current_step_index=0,
        execution_results=[],
        tool_outputs={},
        error_context=None,
        retry_count=0,
        response_text="",
        should_continue=True,
        trace_id=trace_id or str(uuid.uuid4())[:8],
        timestamps={"created": time.time()}
    )


# ============================================================================
# Type Guards
# ============================================================================

def has_valid_input(state: AgentState) -> bool:
    """Check if state has valid user input"""
    return bool(state.get("user_input", "").strip())


def has_valid_plan(state: AgentState) -> bool:
    """Check if state has a valid execution plan"""
    plan = state.get("plan")
    return plan is not None and len(plan.get("steps", [])) > 0


def is_plan_complete(state: AgentState) -> bool:
    """Check if all plan steps are complete"""
    plan = state.get("plan")
    if not plan:
        return True
    results = state.get("execution_results", [])
    return len(results) >= len(plan.get("steps", []))


def can_retry(state: AgentState, max_retries: int = 3) -> bool:
    """Check if we can retry after error"""
    return state.get("retry_count", 0) < max_retries


def has_error(state: AgentState) -> bool:
    """Check if state has an error context"""
    return state.get("error_context") is not None
