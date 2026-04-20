import json
import os
import sys
import importlib.util
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
                    "enabled": False
                },
                "playwright": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["@playwright/mcp@latest"],
                    "enabled": True
                },
                "diagnostic-mcp": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["-m", "system_diagnosis_mcp"],
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
        return self._convert_to_langchain_config(config)
    
    def convert_config_dict_to_langchain(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an already-loaded config dict (without reloading from file).
        Useful when config is already passed in memory.
        """
        return self._convert_to_langchain_config(config)
    
    def _convert_to_langchain_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method to convert config dict to LangChain format"""
        mcp_servers = config.get("mcp_servers", {})
        server_config = {}
        for name, details in mcp_servers.items():
            # Skip disabled servers
            if not details.get("enabled", True):
                continue
            
            transport = details.get("transport", "http")
            
            if transport in ("http", "streamable_http"):
                url = details.get("url")
                if url:
                    server_config[name] = {
                        "transport": "http",  # MultiServerMCPClient uses "http"
                        "url": url
                    }
            elif transport == "stdio":
                command = details.get("command")
                if command:
                    args = details.get("args", [])
                    env = details.get("env", None)  # Optional env vars

                    # Skip stdio python module servers that are not importable.
                    if not self._is_stdio_server_available(command, args):
                        print(
                            f"[MCP Config] Skipping '{name}' because its stdio target is not available in this Python environment.",
                            flush=True,
                        )
                        continue
                    
                    server_config[name] = {
                        "transport": "stdio",
                        "command": command,
                        "args": args
                    }
                    if env:
                        server_config[name]["env"] = env
                        
        return server_config

    def _is_stdio_server_available(self, command: str, args: List[str]) -> bool:
        """
        Best-effort validation for stdio MCP entries.
        For Python module launchers (`python -m module_name`), ensure module exists.
        """
        if not command:
            return False

        normalized = command.lower()
        is_python_cmd = normalized.endswith("python") or normalized.endswith("python.exe")
        if not is_python_cmd:
            return True

        if not args or len(args) < 2:
            return True

        if args[0] != "-m":
            return True

        module_name = args[1]
        return importlib.util.find_spec(module_name) is not None
