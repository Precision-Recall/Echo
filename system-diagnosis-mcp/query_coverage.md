# What These 15 Granular Tools Can Answer

## The Difference: Composability

**NEW (15 granular tools):**
- ✅ "Why is my computer slow?" → `get-cpu-usage` + `get-memory-usage` + `get-disk-io` (agent decides)
- ✅ "What's using my CPU?" → `get-cpu-usage` (precise)
- ✅ "Close Chrome" → `get-process-info("chrome")` → `kill-process(pid)` (two-step workflow)
- ✅ "Is Windows Defender on?" → `check-windows-defender` (precise)

---

## Query → Tool Mapping Examples

### Performance Queries

| User Query | Tools Used | Result |
|------------|-----------|---------|
| "Why is my computer slow?" | `get-cpu-usage`, `get-memory-usage`, `get-disk-io` | Agent identifies bottleneck |
| "What's using all my RAM?" | `get-memory-usage` | Lists top memory hogs |
| "Is my CPU overheating?" | `get-cpu-usage` | Shows CPU load + top processes |
| "What's Chrome doing?" | `get-process-info("chrome")` | Shows all Chrome instances |
| "My disk is constantly busy" | `get-disk-io` | Shows which processes writing |

### Network Queries

| User Query | Tools Used | Result |
|------------|-----------|---------|
| "Is my internet working?" | `test-internet` | Tests connectivity |
| "Why can't I load websites?" | `get-network-status` → `test-internet` → `flush-dns` | Diagnoses + fixes |
| "Check my WiFi" | `get-network-status` | Shows adapter status |
| "Fix my network" | `get-network-status` → `renew-ip` | Auto-fixes if possible |

### Security Queries

| User Query | Tools Used | Result |
|------------|-----------|---------|
| "Is Windows Defender on?" | `check-windows-defender` | Shows Defender status |
| "Am I protected?" | `check-windows-defender` + `check-firewall` | Shows protection status |
| "Check for updates" | `check-windows-updates` | Lists pending updates |
| "Is my firewall enabled?" | `check-firewall` | Shows firewall profiles |

### Storage Queries

| User Query | Tools Used | Result |
|------------|-----------|---------|
| "How much disk space left?" | `get-disk-usage` | Shows all drives |
| "What's taking up space?" | `get-disk-usage` → `find-large-files` | Identifies large files |
| "Find big files in Downloads" | `find-large-files("Downloads")` | Lists files > 100MB |
| "Why is C: drive full?" | `get-disk-usage` → `find-large-files("C:\\")` | Identifies space hogs |

### Process Management

| User Query | Tools Used | Result |
|------------|-----------|---------|
| "What is svchost.exe?" | `get-process-info("svchost")` | Explains process |
| "Close Spotify" | `get-process-info("spotify")` → `kill-process` | Terminates process |
| "Stop all Chrome instances" | `get-process-info("chrome")` → multiple `kill-process` | Closes all |
| "Why is python.exe running?" | `get-process-info("python")` | Shows command line |

### Battery Queries (Laptops)

| User Query | Tools Used | Result |
|------------|-----------|---------|
| "How much battery left?" | `get-battery-info` | Shows percentage |
| "Battery status?" | `get-battery-info` | Shows charge + time remaining |
| "Am I plugged in?" | `get-battery-info` | Shows charging status |

---

## Complex Multi-Tool Workflows

### Scenario 1: "My computer is slow"
**Agent reasoning:**
1. `get-cpu-usage` → CPU at 45%, not the issue
2. `get-memory-usage` → Memory at 92%, critical!
3. Top consumer: Chrome using 4.2GB
4. **Response:** "Chrome is using 4.2GB of RAM, causing memory pressure. Close or restart it?"

### Scenario 2: "Internet not working"
**Agent reasoning:**
1. `get-network-status` → Adapter is UP
2. `test-internet` → Can't reach servers, but DNS working
3. Gateway ping fails
4. `renew-ip` → Fixes it
5. **Response:** "Network adapter was up but had a bad IP lease. I renewed it and you're back online."

### Scenario 3: "Why is my laptop dying so fast?"
**Agent reasoning:**
1. `get-battery-info` → Battery at 45%, discharging fast
2. `get-cpu-usage` → CPU at 85%
3. Top consumer: Windows Update at 60% CPU
4. **Response:** "Windows Update is running in background, using 60% CPU and draining battery. It should finish in about 15 minutes, or I can pause it."

### Scenario 4: "Am I secure?"
**Agent reasoning:**
1. `check-windows-defender` → Disabled!
2. `check-firewall` → Enabled
3. `check-windows-updates` → 8 pending, 2 critical
4. **Response:** "Critical issue: Windows Defender is off. You also have 2 critical security updates pending. Enable Defender immediately."

---

## Coverage Analysis

### With 3 Monolithic Tools:
- ✅ 3 specific workflows
- ❌ No flexibility
- ❌ Can't combine tools
- ❌ All-or-nothing responses

### With 15 Granular Tools:
- ✅ 50+ possible queries
- ✅ Agent chooses relevant tools
- ✅ Can chain tools for workflows
- ✅ Precise, targeted responses

---

## Implementation Strategy

### Add to MCP Server:

```python
# In your Windows-MCP server

from granular_diagnostic_tools import MCP_TOOL_DEFINITIONS

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    diagnostic_tools = []
    
    for tool_def in MCP_TOOL_DEFINITIONS:
        diagnostic_tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def.get("parameters", {
                "type": "object",
                "properties": {},
                "required": []
            })
        ))
    
    return [
        *EXISTING_WINDOWS_TOOLS,
        *diagnostic_tools
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[Any]:
    # Find tool in definitions
    for tool_def in MCP_TOOL_DEFINITIONS:
        if tool_def["name"] == name:
            result = tool_def["function"](**arguments)
            return [{"type": "text", "text": result}]
    
    # ... handle other tools
```

### Update Voice Agent Prompt:

```
You now have 15 system diagnostic tools. Use them intelligently:

- For vague queries ("slow computer"), use multiple tools to identify root cause
- For specific queries ("CPU usage"), use the precise tool
- For workflows ("close Chrome"), chain tools: get-process-info → kill-process
- Always explain what you found before taking action
- Ask confirmation before destructive operations (kill-process, renew-ip)

Available tools:
- System metrics: get-cpu-usage, get-memory-usage, get-disk-usage, get-disk-io
- Network: get-network-status, test-internet, flush-dns, renew-ip
- Security: check-windows-defender, check-firewall, check-windows-updates
- Processes: get-process-info, kill-process
- Storage: find-large-files
- Battery: get-battery-info
```

---

## Why This Is Better

### 1. **Scales to any query**
Not limited to 3 pre-programmed scenarios

### 2. **Agent decides complexity**
"What's my CPU?" → 1 tool
"Why is my computer slow?" → 3 tools
Agent figures it out

### 3. **Composable workflows**
Close a process: `get-process-info` → `kill-process`
Fix network: `test-internet` → `flush-dns` → `renew-ip`

### 4. **Precise responses**
Don't run full security audit when user just asks about Defender

### 5. **Extensible**
Add more tools easily: `get-gpu-usage`, `check-driver-updates`, `optimize-startup`

---

## The Real Answer

**You don't need 3 monolithic tools that only work for 3 queries.**

**You need 15+ granular tools that the agent composes for ANY query.**

That's what makes it a platform, not a demo.
