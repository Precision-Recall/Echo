# System Diagnosis MCP - Tools Reference

A comprehensive collection of **15 granular diagnostic tools** designed as composable building blocks for system diagnostics. These tools enable AI agents to answer any system query by combining smaller, focused operations.

---

## Overview

| Category | Tools | Purpose |
|----------|-------|---------|
| **System Metrics** | 5 tools | Monitor CPU, memory, disk, network, and battery |
| **Process Management** | 2 tools | Inspect and terminate processes |
| **Security** | 3 tools | Check Defender, firewall, and updates |
| **Network Diagnostics** | 3 tools | Test connectivity and troubleshoot |
| **System Cleanup** | 1 tool | Find large files |

---

## System Metrics Tools (Observation Layer)

### `get-cpu-usage`

Get current CPU usage breakdown with top consumers.

| Property | Type | Description |
|----------|------|-------------|
| `overall_percent` | float | Total CPU usage percentage |
| `per_core` | array | Usage per CPU core |
| `top_consumers` | array | Top 5 processes by CPU usage |
| `status` | string | `"high"` (>80%), `"normal"` (>50%), or `"low"` |

**Use when:** User asks about CPU, performance, or "what's using my processor"

---

### `get-memory-usage`

Get memory/RAM usage statistics and top consumers.

| Property | Type | Description |
|----------|------|-------------|
| `total_gb` | float | Total RAM installed |
| `used_gb` | float | RAM currently in use |
| `available_gb` | float | RAM available |
| `percent` | float | Memory usage percentage |
| `top_consumers` | array | Top 5 processes by memory (>50MB) |
| `status` | string | `"critical"` (>90%), `"high"` (>80%), or `"normal"` |

**Use when:** User asks about memory, RAM, or "why is everything slow"

---

### `get-disk-usage`

Get disk space information for all drives.

**Returns array of drives with:**

| Property | Type | Description |
|----------|------|-------------|
| `drive` | string | Drive letter/mount point |
| `filesystem` | string | Filesystem type (NTFS, etc.) |
| `total_gb` | float | Total capacity |
| `used_gb` | float | Used space |
| `free_gb` | float | Available space |
| `percent` | float | Usage percentage |
| `status` | string | `"critical"` (>90%), `"warning"` (>80%), or `"ok"` |

**Use when:** User asks about disk space, storage, or "running out of space"

---

### `get-disk-io`

Get disk I/O statistics and identify heavy disk activity.

| Property | Type | Description |
|----------|------|-------------|
| `read_mb_per_sec` | float | Current disk read speed |
| `write_mb_per_sec` | float | Current disk write speed |
| `total_mb_per_sec` | float | Combined I/O rate |
| `top_io_processes` | array | Processes performing heavy I/O (>10MB) |
| `status` | string | `"heavy"` (>50 MB/s) or `"normal"` |

**Use when:** User asks "why is my disk so busy" or "what's writing to disk"

---

### `get-network-status`

Get network adapter status and internet connectivity.

| Property | Type | Description |
|----------|------|-------------|
| `internet_connected` | boolean | Whether internet is reachable |
| `adapters` | array | Network adapters with Name, Status, LinkSpeed |
| `active_connections` | integer | Number of active network connections |
| `status` | string | `"online"` or `"offline"` |

**Use when:** User asks about network, WiFi, or internet connectivity

---

### `get-battery-info`

Get battery status for laptops.

| Property | Type | Description |
|----------|------|-------------|
| `present` | boolean | Whether battery exists |
| `percent` | float | Battery charge percentage |
| `plugged` | boolean | Whether charger is connected |
| `time_remaining_minutes` | integer | Estimated time remaining (null if unknown) |
| `status` | string | `"charging"` or `"discharging"` |

**Use when:** User asks about battery, power, or "how much battery left"

> **Note:** Returns `{"present": false}` on desktop systems.

---

## Process Management Tools (Action Layer)

### `get-process-info`

Get detailed information about a specific process by name.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `process_name` | string | ✅ | Name of the process (e.g., `"chrome.exe"`, `"python"`) |

**Returns:**

| Property | Type | Description |
|----------|------|-------------|
| `process_name` | string | Queried process name |
| `instances_found` | integer | Number of matching instances |
| `instances` | array | Details per instance (pid, cpu_percent, memory_mb, status, command_line) |

**Use when:** User asks "what is X process" or "why is X using so much"

---

### `kill-process`

Terminate a process by PID.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `pid` | integer | ✅ | Process ID to terminate |

**Returns:**

| Property | Type | Description |
|----------|------|-------------|
| `success` | boolean | Whether termination succeeded |
| `message` | string | Result description |

> [!WARNING]
> **Always confirm with the user before calling this tool.** Use only when user explicitly asks to close/kill a process.

---

## Security Tools (Observation Layer)

### `check-windows-defender`

Check Windows Defender antivirus status.

| Property | Type | Description |
|----------|------|-------------|
| `antivirus_enabled` | boolean | Whether Defender is active |
| `real_time_protection` | boolean | Real-time scanning status |
| `last_updated` | string | Last virus definition update timestamp |
| `status` | string | `"protected"` or `"vulnerable"` |

**Use when:** User asks about antivirus, protection, or Defender

---

### `check-firewall`

Check Windows Firewall status for all network profiles.

| Property | Type | Description |
|----------|------|-------------|
| `profiles` | array | List of profiles (Domain, Private, Public) with name and enabled status |
| `all_enabled` | boolean | Whether firewall is on for all profiles |

**Use when:** User asks about firewall or network security

---

### `check-windows-updates`

Check for pending Windows updates including critical patches.

| Property | Type | Description |
|----------|------|-------------|
| `pending_count` | integer | Number of updates available |
| `critical_count` | integer | Number of critical/security updates |
| `status` | string | `"critical"`, `"needs_update"`, or `"up_to_date"` |

**Use when:** User asks about updates or "is my system updated"

---

## Network Diagnostic Tools (Action Layer)

### `flush-dns`

Flush DNS cache to resolve DNS-related issues.

| Property | Type | Description |
|----------|------|-------------|
| `success` | boolean | Whether operation succeeded |
| `message` | string | Result description |

**Use when:** User reports DNS issues or "websites won't load"

---

### `renew-ip`

Release and renew DHCP IP address.

| Property | Type | Description |
|----------|------|-------------|
| `success` | boolean | Whether operation succeeded |
| `message` | string | Result description |

> [!WARNING]
> This will briefly disconnect the network connection.

**Use when:** User has network connectivity issues or IP conflicts

---

### `test-internet`

Test internet connectivity by pinging reliable servers.

| Property | Type | Description |
|----------|------|-------------|
| `google_reachable` | boolean | Can reach Google DNS (8.8.8.8) |
| `cloudflare_reachable` | boolean | Can reach Cloudflare DNS (1.1.1.1) |
| `dns_working` | boolean | Can resolve domain names |
| `status` | string | `"online"` or `"offline"` |

**Use when:** User asks "is my internet working" or "test connection"

---

## System Cleanup Tools (Action Layer)

### `find-large-files`

Find large files in a directory to identify space usage.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `directory` | string | ✅ | - | Path to search (e.g., `"C:\\Users\\Username\\Downloads"`) |
| `min_size_mb` | integer | ❌ | 100 | Minimum file size in MB |
| `max_depth` | integer | ❌ | 3 | Maximum directory depth to scan |

**Returns:**

| Property | Type | Description |
|----------|------|-------------|
| `directory` | string | Searched directory |
| `files_scanned` | integer | Number of files scanned |
| `max_depth` | integer | Depth limit used |
| `files_found` | integer | Number of large files found |
| `total_size_gb` | float | Combined size of large files |
| `files` | array | Top 20 large files (path, size_mb, modified) |

> **Note:** Scans are limited to 10,000 files to prevent timeouts.

**Use when:** User asks "what's taking up space" or "find large files"

---

## Tool Composition Examples

These granular tools can be combined by the agent to answer complex queries:

| User Query | Tools to Combine |
|------------|------------------|
| "Why is my computer slow?" | `get-cpu-usage` + `get-memory-usage` + `get-disk-io` |
| "Is my computer secure?" | `check-windows-defender` + `check-firewall` + `check-windows-updates` |
| "Fix my internet" | `get-network-status` → `test-internet` → `flush-dns` → `renew-ip` |
| "What's using all my RAM?" | `get-memory-usage` → `get-process-info` (for top consumers) |
| "Clean up my disk" | `get-disk-usage` → `find-large-files` |

---

## Dependencies

- **Python 3.x**
- **psutil** - Cross-platform process and system utilities
- **Windows PowerShell** - Required for security and update checks
