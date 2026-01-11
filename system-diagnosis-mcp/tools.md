# System Diagnosis MCP

A comprehensive Model Context Protocol (MCP) server providing 24 diagnostic and automation tools for Windows desktop environments. Designed for integration with AI voice agents and desktop automation workflows.

## Overview

This module extends AI agent capabilities with granular system monitoring, application management, and troubleshooting tools. Each tool follows a composable design pattern, returning structured JSON responses suitable for LLM consumption.

## Installation

```python
from system_diagnosis_mcp import MCP_TOOL_DEFINITIONS
```

**Requirements:**
- Python 3.10+
- `psutil` - Cross-platform process and system utilities
- Windows 10/11 (PowerShell access required for certain tools)

---

## Tool Categories

### System Monitoring

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get-cpu-usage` | CPU utilization metrics and top consumers | None |
| `get-memory-usage` | RAM statistics and memory-intensive processes | None |
| `get-disk-usage` | Storage capacity across all mounted drives | None |
| `get-disk-io` | Real-time disk read/write throughput | None |
| `get-battery-info` | Battery status for portable devices | None |

### Network Diagnostics

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get-network-status` | Adapter status and connectivity state | None |
| `test-internet` | Connectivity verification via DNS ping | None |
| `flush-dns` | Clear DNS resolver cache | None |
| `renew-ip` | DHCP lease renewal | None |

### Security Assessment

| Tool | Purpose | Parameters |
|------|---------|------------|
| `check-windows-defender` | Antivirus and real-time protection status | None |
| `check-firewall` | Firewall profile status (Domain/Private/Public) | None |
| `check-windows-updates` | Pending update count including critical patches | None |

### Process Management

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get-process-info` | Detailed process inspection | `process_name: string` |
| `kill-process` | Process termination | `pid: integer` |

### Application Control

| Tool | Purpose | Parameters |
|------|---------|------------|
| `launch-app` | Application launcher with common app shortcuts | `app_name: string` |
| `get-running-apps` | Enumerate visible application windows | None |
| `focus-window` | Window focus management | `app_name: string` |

### Hardware Information

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get-system-info` | OS, CPU, RAM, and uptime details | None |
| `get-gpu-usage` | GPU utilization and VRAM (NVIDIA + integrated) | None |
| `get-screen-info` | Display resolution and monitor configuration | None |

### Troubleshooting

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get-recent-errors` | Windows Event Log errors (24h window) | None |
| `check-disk-health` | SMART health status for physical drives | None |
| `get-bluetooth-devices` | Paired and connected Bluetooth peripherals | None |

### Storage Management

| Tool | Purpose | Parameters |
|------|---------|------------|
| `find-large-files` | Locate files exceeding size threshold | `directory: string`, `min_size_mb?: integer` |

---

## Response Format

All tools return JSON-formatted strings with consistent structure:

```json
{
  "status": "normal|warning|critical",
  "data": { ... },
  "message": "Human-readable summary"
}
```

### Example: `get-system-info`

```json
{
  "os_name": "Microsoft Windows 11 Pro",
  "os_version": "10.0.22631",
  "processor": "AMD Ryzen 9 5900X",
  "architecture": "AMD64",
  "ram_gb": 32.0,
  "cpu_cores": 12,
  "cpu_threads": 24,
  "uptime_hours": 72.5
}
```

### Example: `get-gpu-usage` (NVIDIA)

```json
{
  "gpu_count": 1,
  "gpus": [{
    "name": "NVIDIA GeForce RTX 3080",
    "type": "nvidia",
    "memory_total_mb": 10240,
    "memory_used_mb": 2048,
    "utilization_percent": 15,
    "temperature_c": 45
  }],
  "nvidia_available": true
}
```

---

## Supported Applications

The `launch-app` tool supports the following application aliases:

| Category | Applications |
|----------|--------------|
| **Productivity** | `notepad`, `calculator`, `paint`, `wordpad` |
| **Browsers** | `chrome`, `firefox`, `edge`, `brave` |
| **Development** | `vscode`, `terminal`, `powershell`, `cmd` |
| **Communication** | `discord`, `slack`, `teams`, `zoom` |
| **Media** | `spotify`, `vlc` |
| **System** | `explorer`, `settings`, `control`, `task manager` |

---

## Integration

### With MCP Server

```python
from system_diagnosis_mcp import MCP_TOOL_DEFINITIONS

# Register tools with your MCP server
for tool in MCP_TOOL_DEFINITIONS:
    mcp_server.register_tool(
        name=tool["name"],
        description=tool["description"],
        handler=tool["function"],
        parameters=tool.get("parameters", {})
    )
```

### Direct Usage

```python
from system_diagnosis_mcp import get_cpu_usage

# Get CPU metrics
cpu_data = get_cpu_usage()
print(cpu_data)
```

---

## Security Considerations

- **`kill-process`**: Requires user confirmation before execution
- **`renew-ip`**: Temporarily disconnects network connectivity
- **Event Log access**: Requires appropriate Windows permissions
- **SMART data**: Requires access to physical disk information

---

## License

Part of the Echo Desktop Agent project.
