#!/usr/bin/env python3
"""
Import Verification Script for Echo Electron Bridge

Run this script to verify all imports are working before starting the Electron app.
"""

import sys
import os

# Setup path (same as electron_bridge.py)
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(current_file)
electron_app_dir = os.path.dirname(backend_dir)
project_root = os.path.dirname(electron_app_dir)
sys.path.insert(0, project_root)

print("=" * 60)
print("Echo Electron Bridge - Import Verification")
print("=" * 60)
print()

# Check paths
print(f"✓ Current file: {current_file}")
print(f"✓ Backend dir: {backend_dir}")
print(f"✓ Electron app dir: {electron_app_dir}")
print(f"✓ Project root: {project_root}")
print()

# Check .env file
env_path = os.path.join(project_root, '.env')
if os.path.exists(env_path):
    print(f"✓ .env file found at: {env_path}")
else:
    print(f"✗ .env file NOT found at: {env_path}")
    print("  Please create a .env file with your GEMINI_API_KEY")
print()

# Test imports
print("Testing imports...")
print("-" * 60)

try:
    from dotenv import load_dotenv
    print("✓ dotenv")
except ImportError as e:
    print(f"✗ dotenv: {e}")
    sys.exit(1)

try:
    from src.agent import ThinkingLogger, ModelConfig, AgentMode
    print("✓ src.agent.ThinkingLogger")
    print("✓ src.agent.ModelConfig")
    print("✓ src.agent.AgentMode")
except ImportError as e:
    print(f"✗ src.agent: {e}")
    sys.exit(1)

try:
    from src.agent.live_client import GeminiLiveClient
    print("✓ src.agent.live_client.GeminiLiveClient")
except ImportError as e:
    print(f"✗ src.agent.live_client: {e}")
    sys.exit(1)

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    print("✓ langchain_mcp_adapters.client.MultiServerMCPClient")
except ImportError as e:
    print(f"✗ langchain_mcp_adapters: {e}")
    print("  Install with: uv sync")
    sys.exit(1)

try:
    import pyaudio
    print("✓ pyaudio")
except ImportError as e:
    print(f"✗ pyaudio: {e}")
    print("  Install with: pip install pyaudio")
    sys.exit(1)

try:
    from google import genai
    print("✓ google.genai")
except ImportError as e:
    print(f"✗ google.genai: {e}")
    print("  Install with: pip install google-genai")
    sys.exit(1)

print()
print("-" * 60)
print("✅ All imports successful!")
print()

# Check API key
load_dotenv(os.path.join(project_root, '.env'))
api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

if api_key:
    print(f"✓ GEMINI_API_KEY found (length: {len(api_key)})")
else:
    print("✗ GEMINI_API_KEY not set in .env")
    print("  Please add your API key to .env file")
print()

# Test model config
print("Testing ModelConfig...")
print("-" * 60)
try:
    config = ModelConfig.get_config(AgentMode.VOICE)
    print(f"✓ VOICE mode model: {config.model_name}")
    print(f"  Temperature: {config.temperature}")
except Exception as e:
    print(f"✗ ModelConfig error: {e}")
    sys.exit(1)

print()

# Test logger creation
print("Testing ElectronLogger...")
print("-" * 60)
try:
    logger = ThinkingLogger()
    logger.log_thought("Test thought message")
    logger.log_action("test_tool", {"arg": "value"})
    logger.log_observation("Test observation")
    logger.log_result("Test result")
    print("✓ ThinkingLogger works correctly")
except Exception as e:
    print(f"✗ ThinkingLogger error: {e}")
    sys.exit(1)

print()

# Test AudioManager
print("Testing AudioManager...")
print("-" * 60)
try:
    from src.agent.audio import AudioManager
    audio = AudioManager()
    print(f"✓ AudioManager created")
    print(f"  Input rate: {audio.INPUT_RATE}Hz")
    print(f"  Output rate: {audio.OUTPUT_RATE}Hz")
    print(f"  Chunk size: {audio.CHUNK}")
    
    # Check audio devices
    device_count = audio.p.get_device_count()
    print(f"  Available audio devices: {device_count}")
    
    # List devices
    for i in range(device_count):
        info = audio.p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"    Input: {info['name']}")
        if info['maxOutputChannels'] > 0:
            print(f"    Output: {info['name']}")
    
    audio.close()
except Exception as e:
    print(f"✗ AudioManager error: {e}")
    print("  Audio may not work correctly")

print()

# Summary
print("=" * 60)
print("✅ Verification Complete!")
print("=" * 60)
print()
print("Next steps:")
print("1. Ensure Windows-MCP is running: uvx windows-mcp --transport streamable-http --port 8000")
print("2. Run electron bridge: python electron_bridge.py")
print("3. Or start Electron app: cd .. && npm start")
print()

