import json
import os
import sys
from typing import Dict, Any, List

class MCPConfigManager:
    """
    Manages loading and saving of MCP configuration (mcp_config.json).
    Supports both 'stdio' (command line) and 'http' (SSE) transports.
    """
    
    DEFAULT_CONFIG_FILENAME = "mcp_config.json"
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to current working directory or user home
            config_dir = os.getcwd()
        self.config_path = os.path.join(config_dir, self.DEFAULT_CONFIG_FILENAME)
        self._ensure_config_exists()
        
    def _ensure_config_exists(self):
        """Create default config if it doesn't exist"""
        if not os.path.exists(self.config_path):
            default_config = self._get_default_config()
            self.save_config(default_config)
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Return the default configuration structure"""
        return {
            "enable_diagnostic_tools": True,
            "mcp_servers": {
                "windows-mcp": {
                    "transport": "streamable_http",
                    "url": "http://127.0.0.1:8000/mcp",
                    "enabled": True
                }
            }
        }

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Migrate or fix missing keys
            defaults = self._get_default_config()
            if "enable_diagnostic_tools" not in config:
                config["enable_diagnostic_tools"] = defaults["enable_diagnostic_tools"]
            if "mcp_servers" not in config:
                config["mcp_servers"] = defaults["mcp_servers"]
                
            return config
        except Exception as e:
            print(f"[ERROR] Failed to load MCP config: {e}", flush=True)
            return self._get_default_config()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save MCP config: {e}", flush=True)
            return False

    def get_langchain_config(self) -> Dict[str, Any]:
        """
        Convert stored config into the dictionary format expected by 
        MultiServerMCPClient.
        """
        config = self.load_config()
        mcp_servers = config.get("mcp_servers", {})
        
        server_config = {}
        for name, details in mcp_servers.items():
            # Skip disabled servers
            if not details.get("enabled", True):
                continue
            
            transport = details.get("transport", "http")
            
            if transport == "http":
                url = details.get("url")
                if url:
                    server_config[name] = {
                        "transport": "http",
                        "url": url
                    }
            elif transport == "stdio":
                command = details.get("command")
                if command:
                    args = details.get("args", [])
                    env = details.get("env", None)  # Optional env vars
                    
                    server_config[name] = {
                        "transport": "stdio",
                        "command": command,
                        "args": args
                    }
                    if env:
                        server_config[name]["env"] = env
                        
        return server_config
