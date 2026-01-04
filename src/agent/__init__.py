"""Agent package"""
from .llm_agent import DesktopAgent, AgentMode, ModelConfig
from .thinking_logger import ThinkingLogger, EventType
from .schemas import AgentState, ExecutionPlan, ExecutionStep, StepResult, AgentStateType
from .state_graph import MultiAgentGraph, create_multi_agent_graph
from .planner_agent import PlannerAgent
from .executor_agent import ExecutorAgent
from .voice_agent import VoiceAgent
from .task_router import TaskRouter, TaskComplexity

__all__ = [
    # Original exports
    'DesktopAgent', 'AgentMode', 'ModelConfig', 
    'ThinkingLogger', 'EventType',
    # New multi-agent exports
    'AgentState', 'ExecutionPlan', 'ExecutionStep', 'StepResult', 'AgentStateType',
    'MultiAgentGraph', 'create_multi_agent_graph',
    'PlannerAgent', 'ExecutorAgent', 'VoiceAgent',
    # Task routing
    'TaskRouter', 'TaskComplexity'
]

