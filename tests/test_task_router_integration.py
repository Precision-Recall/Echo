"""
Integration Tests for TaskRouter with Entry Points

Tests:
1. TaskRouter classification logic (SIMPLE vs COMPLEX) using mocked LLM
2. TaskRouter with mocked MCP client
3. Integration path: main.py -> DesktopAgent -> GeminiLiveClient
4. Integration path: electron_bridge.py -> DesktopAgent -> GeminiLiveClient
"""

import pytest
import asyncio
import sys
import os
import json
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agent.task_router import TaskRouter, TaskComplexity


class TestTaskRouterClassification:
    """Test TaskRouter LLM-based classification"""
    
    def setup_method(self):
        self.router = TaskRouter(api_key="mock-key")
        # Mock the client
        self.router.client = AsyncMock()
        self.router.client.aio.models.generate_content = AsyncMock()
    
    def _mock_llm_response(self, complexity: str, reason: str = "test"):
        """Helper to mock LLM JSON response"""
        response = Mock()
        response.text = json.dumps({"complexity": complexity, "reason": reason})
        self.router.client.aio.models.generate_content.return_value = response

    @pytest.mark.asyncio
    async def test_simple_routing(self):
        """Test simple task classification"""
        self._mock_llm_response("simple")
        complexity = await self.router.get_routing_strategy("what time is it")
        assert complexity == TaskComplexity.SIMPLE
        
    @pytest.mark.asyncio
    async def test_complex_routing(self):
        """Test complex task classification"""
        self._mock_llm_response("complex")
        complexity = await self.router.get_routing_strategy("organize files")
        assert complexity == TaskComplexity.COMPLEX
        
    @pytest.mark.asyncio
    async def test_routing_fallback_on_error(self):
        """Should default to SIMPLE on LLM error"""
        self.router.client.aio.models.generate_content.side_effect = Exception("API Error")
        complexity = await self.router.get_routing_strategy("anything")
        assert complexity == TaskComplexity.SIMPLE


class TestTaskRouterEscalation:
    """Test EAFP escalation logic"""
    
    def setup_method(self):
        self.router = TaskRouter()
    
    def test_escalate_on_error(self):
        """Errors should trigger escalation"""
        error = Exception("Tool execution failed")
        assert self.router.should_escalate("any command", error=error) is True
    
    def test_escalate_after_multiple_failures(self):
        """Repeated failures should escalate"""
        # Simulate two failures
        self.router.should_escalate("cmd", error=Exception("fail 1"))
        self.router.should_escalate("cmd", error=Exception("fail 2"))
        # Now even without error, should escalate
        assert self.router.should_escalate("cmd", error=None) is True


class TestGeminiLiveClientRouterIntegration:
    """Test TaskRouter integration with GeminiLiveClient"""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        logger = Mock()
        logger.log_thought = Mock()
        logger.log_result = Mock()
        logger.log_action = Mock()
        logger.log_observation = Mock()
        logger.log_error = Mock()
        return logger
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mock MCP client"""
        client = AsyncMock()
        client.get_tools = AsyncMock(return_value=[])
        return client
    
    def test_live_client_has_task_router(self, mock_logger, mock_mcp_client):
        """GeminiLiveClient should have TaskRouter"""
        from src.agent.live_client import GeminiLiveClient
        
        client = GeminiLiveClient(
            api_key="test-key",
            model_name="test-model",
            logger=mock_logger,
            mcp_client=mock_mcp_client
        )
        
        assert client.task_router is not None
        assert isinstance(client.task_router, TaskRouter)

    @pytest.mark.asyncio
    async def test_route_calls_get_routing_strategy(self, mock_logger, mock_mcp_client):
        """Verify _route_complex_task calls async get_routing_strategy"""
        from src.agent.live_client import GeminiLiveClient
        
        mock_graph = Mock()
        mock_graph.run_for_voice = AsyncMock(return_value="Done")
        
        client = GeminiLiveClient(
            api_key="test-key",
            model_name="test-model",
            logger=mock_logger,
            mcp_client=mock_mcp_client,
            multi_agent_graph=mock_graph
        )
        
        # Mock the router on the client instance
        client.task_router.get_routing_strategy = AsyncMock(return_value=TaskComplexity.COMPLEX)
        client._pending_transcript = "complex task"
        
        await client._route_complex_task(AsyncMock())
        
        client.task_router.get_routing_strategy.assert_called_once_with("complex task")
        mock_graph.run_for_voice.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
