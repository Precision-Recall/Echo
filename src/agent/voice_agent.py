"""
Voice Agent - Handles STT/TTS I/O layer
Uses Gemini Live for voice interaction
"""

from typing import Optional
from .schemas import AgentState, AgentStateType
from .thinking_logger import ThinkingLogger


class VoiceAgent:
    """
    Voice I/O layer for the multi-agent system.
    Handles speech-to-text input and text-to-speech output.
    
    In VOICE mode, this integrates with GeminiLiveClient.
    In TEXT mode, this passes through directly.
    """
    
    def __init__(self, logger: ThinkingLogger):
        self.logger = logger
        self._audio_manager = None
    
    async def voice_input_node(self, state: AgentState) -> AgentState:
        """
        Node function: Process voice input.
        
        For now, this is a passthrough - actual STT is handled by
        GeminiLiveClient. This node validates and prepares input.
        
        Args:
            state: State with user_input from STT
            
        Returns:
            Updated state ready for planning
        """
        import time
        
        user_input = state.get("user_input", "").strip()
        
        if not user_input:
            self.logger.log_thought("🎤 Waiting for voice input...")
            state["current_state"] = AgentStateType.LISTENING
            return state
        
        self.logger.log_thought(f"🎤 Received: {user_input}")
        
        # Record timestamp
        timestamps = state.get("timestamps", {})
        timestamps["input_received"] = time.time()
        state["timestamps"] = timestamps
        
        # Transition to planning
        state["current_state"] = AgentStateType.PLANNING
        
        return state
    
    async def voice_output_node(self, state: AgentState) -> AgentState:
        """
        Node function: Deliver voice response.
        
        For now, this logs the response - actual TTS is handled by
        GeminiLiveClient.
        
        Args:
            state: State with response_text
            
        Returns:
            Updated state after response delivery
        """
        import time
        
        response_text = state.get("response_text", "")
        
        if response_text:
            self.logger.log_result(f"🗣️ {response_text}")
        
        # Record timestamp
        timestamps = state.get("timestamps", {})
        timestamps["response_delivered"] = time.time()
        state["timestamps"] = timestamps
        
        # Determine next state
        should_continue = state.get("should_continue", True)
        
        if should_continue:
            # Reset for next interaction
            state["user_input"] = ""
            state["plan"] = None
            state["execution_results"] = []
            state["tool_outputs"] = {}
            state["error_context"] = None
            state["retry_count"] = 0
            state["response_text"] = ""
            state["current_step_index"] = 0
            state["current_state"] = AgentStateType.LISTENING
        else:
            # Session complete - state machine will exit
            self.logger.log_thought("👋 Session ending")
        
        return state
