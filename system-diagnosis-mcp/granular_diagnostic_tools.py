"""
Granular Diagnostic Tools - Composable Building Blocks

Instead of 3 monolithic tools, create 15+ small tools that can answer ANY system query.
The agent decides which tools to use and how to combine them.
"""

import psutil
import subprocess
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# ============================================================================
# SYSTEM METRICS TOOLS (Observation Layer)
# ============================================================================

def get_cpu_usage() -> str:
    """
    Get current CPU usage breakdown
    
    Returns:
    - overall_percent: Total CPU usage
    - per_core: Usage per CPU core
    - top_consumers: Top 5 processes by CPU usage
    
    Use when: User asks about CPU, performance, or "what's using my processor"
    """
    cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
    per_core = psutil.cpu_percent(interval=1, percpu=True)
    
    # Get top CPU consumers
    processes = []
    for proc in psutil.process_iter(['name', 'pid', 'cpu_percent']):
        try:
            info = proc.info
            if info['cpu_percent'] and info['cpu_percent'] > 1:
                processes.append({
                    "name": info['name'],
                    "pid": info['pid'],
                    "cpu_percent": round(info['cpu_percent'], 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    top_consumers = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
    
    return json.dumps({
        "overall_percent": round(cpu_percent, 1),
        "per_core": [round(c, 1) for c in per_core],
        "top_consumers": top_consumers,
        "status": "high" if cpu_percent > 80 else "normal" if cpu_percent > 50 else "low"
    }, indent=2)


def get_memory_usage() -> str:
    """
    Get memory usage statistics
    
    Returns:
    - total_gb: Total RAM installed
    - used_gb: RAM currently in use
    - available_gb: RAM available
    - percent: Memory usage percentage
    - top_consumers: Top 5 processes by memory usage
    
    Use when: User asks about memory, RAM, or "why is everything slow"
    """
    mem = psutil.virtual_memory()
    
    # Get top memory consumers
    processes = []
    for proc in psutil.process_iter(['name', 'pid', 'memory_info']):
        try:
            info = proc.info
            mem_mb = info['memory_info'].rss / 1024 / 1024
            if mem_mb > 50:  # Only processes using > 50MB
                processes.append({
                    "name": info['name'],
                    "pid": info['pid'],
                    "memory_mb": round(mem_mb, 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    top_consumers = sorted(processes, key=lambda x: x['memory_mb'], reverse=True)[:5]
    
    return json.dumps({
        "total_gb": round(mem.total / 1024 / 1024 / 1024, 2),
        "used_gb": round(mem.used / 1024 / 1024 / 1024, 2),
        "available_gb": round(mem.available / 1024 / 1024 / 1024, 2),
        "percent": round(mem.percent, 1),
        "top_consumers": top_consumers,
        "status": "critical" if mem.percent > 90 else "high" if mem.percent > 80 else "normal"
    }, indent=2)


def get_disk_usage() -> str:
    """
    Get disk space information for all drives
    
    Returns list of drives with:
    - drive: Drive letter
    - total_gb: Total capacity
    - used_gb: Used space
    - free_gb: Available space
    - percent: Usage percentage
    
    Use when: User asks about disk space, storage, "running out of space"
    """
    drives = []
    
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            drives.append({
                "drive": partition.mountpoint,
                "filesystem": partition.fstype,
                "total_gb": round(usage.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(usage.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(usage.free / 1024 / 1024 / 1024, 2),
                "percent": round(usage.percent, 1),
                "status": "critical" if usage.percent > 90 else "warning" if usage.percent > 80 else "ok"
            })
        except PermissionError:
            continue
    
    return json.dumps(drives, indent=2)


def get_disk_io() -> str:
    """
    Get disk I/O statistics
    
    Returns:
    - read_mb_per_sec: Current disk read speed
    - write_mb_per_sec: Current disk write speed
    - top_io_processes: Processes performing heavy disk operations
    
    Use when: User asks "why is my disk so busy", "what's writing to disk"
    """
    # Sample I/O twice to calculate rate
    io1 = psutil.disk_io_counters()
    import time
    time.sleep(1)
    io2 = psutil.disk_io_counters()
    
    read_rate = (io2.read_bytes - io1.read_bytes) / 1024 / 1024
    write_rate = (io2.write_bytes - io1.write_bytes) / 1024 / 1024
    
    # Get processes with I/O
    io_processes = []
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            io = proc.io_counters()
            total_io_mb = (io.read_bytes + io.write_bytes) / 1024 / 1024
            if total_io_mb > 10:  # > 10MB I/O
                io_processes.append({
                    "name": proc.info['name'],
                    "pid": proc.info['pid'],
                    "io_mb": round(total_io_mb, 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            continue
    
    top_io = sorted(io_processes, key=lambda x: x['io_mb'], reverse=True)[:5]
    
    return json.dumps({
        "read_mb_per_sec": round(read_rate, 2),
        "write_mb_per_sec": round(write_rate, 2),
        "total_mb_per_sec": round(read_rate + write_rate, 2),
        "top_io_processes": top_io,
        "status": "heavy" if (read_rate + write_rate) > 50 else "normal"
    }, indent=2)


def get_network_status() -> str:
    """
    Get network connection status
    
    Returns:
    - connected: Whether internet is reachable
    - adapters: List of network adapters and their status
    - active_connections: Number of active network connections
    
    Use when: User asks about network, WiFi, internet connectivity
    """
    # Check adapters
    adapters = []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetAdapter | Select-Object Name, Status, LinkSpeed | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            adapter_data = json.loads(result.stdout)
            if not isinstance(adapter_data, list):
                adapter_data = [adapter_data]
            adapters = adapter_data
    except:
        pass
    
    # Check internet connectivity
    internet_ok = False
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", "8.8.8.8"],
            capture_output=True,
            timeout=3
        )
        internet_ok = result.returncode == 0
    except:
        pass
    
    # Get connection count
    connections = len(psutil.net_connections())
    
    return json.dumps({
        "internet_connected": internet_ok,
        "adapters": adapters,
        "active_connections": connections,
        "status": "online" if internet_ok else "offline"
    }, indent=2)


def get_battery_info() -> str:
    """
    Get battery status (for laptops)
    
    Returns:
    - present: Whether battery exists
    - percent: Battery charge percentage
    - plugged: Whether charger is connected
    - time_remaining: Estimated time left
    
    Use when: User asks about battery, power, "how much battery left"
    """
    battery = psutil.sensors_battery()
    
    if battery is None:
        return json.dumps({"present": False, "message": "No battery detected (desktop system)"})
    
    return json.dumps({
        "present": True,
        "percent": round(battery.percent, 1),
        "plugged": battery.power_plugged,
        "time_remaining_minutes": round(battery.secsleft / 60) if battery.secsleft != -1 else None,
        "status": "charging" if battery.power_plugged else "discharging"
    }, indent=2)


# ============================================================================
# PROCESS MANAGEMENT TOOLS (Action Layer)
# ============================================================================

def get_process_info(process_name: str) -> str:
    """
    Get detailed information about a specific process
    
    Args:
        process_name: Name of the process (e.g., "chrome.exe", "python")
    
    Returns information about all instances of the process:
    - pid: Process ID
    - cpu_percent: CPU usage
    - memory_mb: Memory usage
    - status: Running status
    - command_line: Full command line
    
    Use when: User asks "what is X process", "why is X using so much"
    """
    matches = []
    
    for proc in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_info', 'status', 'cmdline']):
        try:
            info = proc.info
            if process_name.lower() in info['name'].lower():
                matches.append({
                    "name": info['name'],
                    "pid": info['pid'],
                    "cpu_percent": round(info['cpu_percent'] or 0, 1),
                    "memory_mb": round(info['memory_info'].rss / 1024 / 1024, 1),
                    "status": info['status'],
                    "command_line": ' '.join(info['cmdline']) if info['cmdline'] else None
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return json.dumps({
        "process_name": process_name,
        "instances_found": len(matches),
        "instances": matches
    }, indent=2)


def kill_process(pid: int) -> str:
    """
    Terminate a process by PID
    
    Args:
        pid: Process ID to terminate
    
    Returns:
        success: Whether termination succeeded
        message: Result description
    
    Use when: User explicitly asks to close/kill a specific process
    WARNING: Ask for confirmation before calling this
    """
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        
        # Wait for termination
        proc.wait(timeout=3)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully terminated {name} (PID: {pid})"
        })
    except psutil.NoSuchProcess:
        return json.dumps({
            "success": False,
            "message": f"Process {pid} not found"
        })
    except psutil.AccessDenied:
        return json.dumps({
            "success": False,
            "message": f"Access denied - cannot terminate PID {pid} (may be system process)"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Failed to terminate: {str(e)}"
        })


# ============================================================================
# SECURITY TOOLS (Observation Layer)
# ============================================================================

def check_windows_defender() -> str:
    """
    Check Windows Defender status
    
    Returns:
    - enabled: Whether Defender is active
    - real_time_protection: Real-time scanning status
    - definitions_updated: Whether virus definitions are current
    
    Use when: User asks about antivirus, protection, Defender
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, "
             "AntivirusSignatureLastUpdated | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            status = json.loads(result.stdout)
            return json.dumps({
                "antivirus_enabled": status.get("AntivirusEnabled", False),
                "real_time_protection": status.get("RealTimeProtectionEnabled", False),
                "last_updated": status.get("AntivirusSignatureLastUpdated", None),
                "status": "protected" if status.get("AntivirusEnabled") else "vulnerable"
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "status": "unknown"})


def check_firewall() -> str:
    """
    Check Windows Firewall status for all network profiles
    
    Returns list of profiles (Domain, Private, Public) with:
    - name: Profile name
    - enabled: Whether firewall is on
    
    Use when: User asks about firewall, network security
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            profiles = json.loads(result.stdout)
            if not isinstance(profiles, list):
                profiles = [profiles]
            
            return json.dumps({
                "profiles": profiles,
                "all_enabled": all(p.get("Enabled", False) for p in profiles)
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def check_windows_updates() -> str:
    """
    Check for pending Windows updates
    
    Returns:
    - pending_count: Number of updates available
    - critical_count: Number of critical updates
    
    Use when: User asks about updates, "is my system updated"
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "$Session = New-Object -ComObject Microsoft.Update.Session; "
             "$Searcher = $Session.CreateUpdateSearcher(); "
             "$Updates = $Searcher.Search('IsInstalled=0'); "
             "$Critical = ($Updates.Updates | Where-Object {$_.MsrcSeverity -eq 'Critical'}).Count; "
             "Write-Output \"$($Updates.Updates.Count),$Critical\""],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            counts = result.stdout.strip().split(',')
            total = int(counts[0]) if len(counts) > 0 else 0
            critical = int(counts[1]) if len(counts) > 1 else 0
            
            return json.dumps({
                "pending_count": total,
                "critical_count": critical,
                "status": "critical" if critical > 0 else "needs_update" if total > 0 else "up_to_date"
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "pending_count": None})


# ============================================================================
# NETWORK DIAGNOSTIC TOOLS (Action Layer)
# ============================================================================

def flush_dns() -> str:
    """
    Flush DNS cache
    
    Use when: User reports DNS issues, "websites won't load", or as troubleshooting step
    """
    try:
        result = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return json.dumps({
            "success": result.returncode == 0,
            "message": "DNS cache flushed successfully" if result.returncode == 0 else "Failed to flush DNS"
        })
    except Exception as e:
        return json.dumps({"success": False, "message": str(e)})


def renew_ip() -> str:
    """
    Release and renew DHCP IP address
    
    Use when: User has network connectivity issues, IP conflict
    WARNING: This will briefly disconnect network
    """
    try:
        # Release
        subprocess.run(["ipconfig", "/release"], capture_output=True, timeout=10)
        # Renew
        result = subprocess.run(["ipconfig", "/renew"], capture_output=True, timeout=15)
        
        return json.dumps({
            "success": result.returncode == 0,
            "message": "IP address renewed" if result.returncode == 0 else "Failed to renew IP"
        })
    except Exception as e:
        return json.dumps({"success": False, "message": str(e)})


def test_internet_connection() -> str:
    """
    Test internet connectivity by pinging reliable servers
    
    Returns:
    - google_reachable: Can reach Google DNS
    - cloudflare_reachable: Can reach Cloudflare DNS
    - dns_working: Can resolve domain names
    
    Use when: User asks "is my internet working", "test connection"
    """
    results = {}
    
    # Test Google DNS
    try:
        result = subprocess.run(
            ["ping", "-n", "2", "-w", "2000", "8.8.8.8"],
            capture_output=True,
            timeout=5
        )
        results["google_reachable"] = result.returncode == 0
    except:
        results["google_reachable"] = False
    
    # Test Cloudflare DNS
    try:
        result = subprocess.run(
            ["ping", "-n", "2", "-w", "2000", "1.1.1.1"],
            capture_output=True,
            timeout=5
        )
        results["cloudflare_reachable"] = result.returncode == 0
    except:
        results["cloudflare_reachable"] = False
    
    # Test DNS resolution
    import socket
    try:
        socket.gethostbyname("google.com")
        results["dns_working"] = True
    except:
        results["dns_working"] = False
    
    results["status"] = "online" if any([results["google_reachable"], results["cloudflare_reachable"]]) else "offline"
    
    return json.dumps(results, indent=2)


# ============================================================================
# SYSTEM CLEANUP TOOLS (Action Layer)
# ============================================================================

def find_large_files(directory: str, min_size_mb: int = 100, max_depth: int = 3) -> str:
    """
    Find large files in a directory (limited depth to prevent long scans)
    
    Args:
        directory: Path to search (e.g., "C:\\Users\\Username\\Downloads")
        min_size_mb: Minimum file size in MB (default: 100)
        max_depth: Maximum directory depth to scan (default: 3)
    
    Returns list of files with:
    - path: Full file path
    - size_mb: File size in megabytes
    - modified: Last modified date
    
    Use when: User asks "what's taking up space", "find large files"
    """
    import os
    from datetime import datetime
    
    large_files = []
    min_bytes = min_size_mb * 1024 * 1024
    start_depth = directory.count(os.sep)
    files_scanned = 0
    max_files_scan = 10000  # Limit total files to prevent timeout
    
    try:
        for root, dirs, files in os.walk(directory):
            # Limit depth to prevent infinite recursion on C:\
            current_depth = root.count(os.sep) - start_depth
            if current_depth >= max_depth:
                dirs.clear()  # Don't descend further
                continue
            
            for file in files:
                files_scanned += 1
                if files_scanned > max_files_scan:
                    break  # Stop if we've scanned too many
                    
                try:
                    filepath = os.path.join(root, file)
                    size = os.path.getsize(filepath)
                    
                    if size >= min_bytes:
                        modified = os.path.getmtime(filepath)
                        large_files.append({
                            "path": filepath,
                            "size_mb": round(size / 1024 / 1024, 2),
                            "modified": datetime.fromtimestamp(modified).isoformat()
                        })
                except (PermissionError, FileNotFoundError, OSError):
                    continue
            
            if files_scanned > max_files_scan:
                break
        
        # Sort by size
        large_files.sort(key=lambda x: x['size_mb'], reverse=True)
        
        return json.dumps({
            "directory": directory,
            "files_scanned": files_scanned,
            "max_depth": max_depth,
            "files_found": len(large_files),
            "total_size_gb": round(sum(f['size_mb'] for f in large_files) / 1024, 2),
            "files": large_files[:20]  # Top 20
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "files_found": 0})


# ============================================================================
# HARDWARE & SYSTEM INFO TOOLS
# ============================================================================

def get_system_info() -> str:
    """
    Get comprehensive system information
    
    Returns:
    - os_name: Windows version
    - os_build: Build number
    - computer_name: PC name
    - processor: CPU model
    - ram_gb: Total RAM
    - architecture: 32/64-bit
    - uptime_hours: System uptime
    
    Use when: User asks "what's my system", "PC specs", "system info"
    """
    import platform
    import os
    
    try:
        # Get Windows version details
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).Caption"],
            capture_output=True,
            text=True,
            timeout=5
        )
        os_name = result.stdout.strip() if result.returncode == 0 else platform.system()
        
        # Get processor info
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_Processor).Name"],
            capture_output=True,
            text=True,
            timeout=5
        )
        processor = result.stdout.strip() if result.returncode == 0 else platform.processor()
        
        # Get uptime
        uptime_seconds = psutil.boot_time()
        import time
        uptime_hours = round((time.time() - uptime_seconds) / 3600, 1)
        
        return json.dumps({
            "os_name": os_name,
            "os_version": platform.version(),
            "os_build": platform.win32_ver()[1] if hasattr(platform, 'win32_ver') else None,
            "computer_name": platform.node(),
            "processor": processor,
            "architecture": platform.machine(),
            "ram_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 1),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "uptime_hours": uptime_hours
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_gpu_usage() -> str:
    """
    Get GPU information and usage (supports NVIDIA and integrated graphics)
    
    Returns:
    - gpus: List of GPUs with name, memory, utilization
    
    Use when: User asks about GPU, graphics card, video memory
    """
    gpus = []
    
    # Try nvidia-smi for NVIDIA GPUs
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 6:
                    gpus.append({
                        "name": parts[0],
                        "type": "nvidia",
                        "memory_total_mb": int(parts[1]),
                        "memory_used_mb": int(parts[2]),
                        "memory_free_mb": int(parts[3]),
                        "utilization_percent": int(parts[4]),
                        "temperature_c": int(parts[5])
                    })
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback: Get GPU info via WMI
    if not gpus:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                gpu_data = json.loads(result.stdout)
                if not isinstance(gpu_data, list):
                    gpu_data = [gpu_data]
                
                for gpu in gpu_data:
                    adapter_ram = gpu.get("AdapterRAM", 0)
                    gpus.append({
                        "name": gpu.get("Name", "Unknown"),
                        "type": "integrated" if "Intel" in gpu.get("Name", "") or "AMD" in gpu.get("Name", "") else "dedicated",
                        "memory_mb": round(adapter_ram / 1024 / 1024) if adapter_ram else "Unknown",
                        "driver_version": gpu.get("DriverVersion", "Unknown")
                    })
        except Exception:
            pass
    
    return json.dumps({
        "gpu_count": len(gpus),
        "gpus": gpus,
        "nvidia_available": any(g.get("type") == "nvidia" for g in gpus)
    }, indent=2)


def get_screen_info() -> str:
    """
    Get display/monitor information
    
    Returns:
    - monitors: List of connected displays
    - primary: Primary display info
    
    Use when: User asks about screen, resolution, display settings, monitors
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object VideoModeDescription, CurrentRefreshRate | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        monitors = []
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                data = [data]
            
            for i, mon in enumerate(data):
                mode = mon.get("VideoModeDescription", "")
                monitors.append({
                    "index": i + 1,
                    "resolution": mode.split(" x ")[0] + " x " + mode.split(" x ")[1].split(" ")[0] if " x " in mode else mode,
                    "refresh_rate": mon.get("CurrentRefreshRate", "Unknown")
                })
        
        # Get more detailed monitor info
        result2 = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance -Namespace root\\wmi -Class WmiMonitorBasicDisplayParams -ErrorAction SilentlyContinue | "
             "Select-Object InstanceName, MaxHorizontalImageSize, MaxVerticalImageSize | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result2.returncode == 0 and result2.stdout.strip():
            try:
                sizes = json.loads(result2.stdout)
                if not isinstance(sizes, list):
                    sizes = [sizes]
                
                for i, size in enumerate(sizes):
                    if i < len(monitors):
                        h = size.get("MaxHorizontalImageSize", 0)
                        v = size.get("MaxVerticalImageSize", 0)
                        if h and v:
                            import math
                            diagonal = round(math.sqrt(h*h + v*v) / 2.54, 1)
                            monitors[i]["size_inches"] = diagonal
            except:
                pass
        
        return json.dumps({
            "monitor_count": len(monitors),
            "monitors": monitors
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# TROUBLESHOOTING TOOLS
# ============================================================================

def get_recent_errors() -> str:
    """
    Get recent Windows Event Log errors (last 24 hours)
    
    Returns:
    - errors: List of recent error events
    - count: Number of errors found
    
    Use when: User reports issues, crashes, or wants to see system errors
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "$yesterday = (Get-Date).AddDays(-1); "
             "Get-WinEvent -FilterHashtable @{LogName='System','Application'; Level=2; StartTime=$yesterday} -MaxEvents 20 -ErrorAction SilentlyContinue | "
             "Select-Object TimeCreated, ProviderName, Id, Message | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            errors = json.loads(result.stdout)
            if not isinstance(errors, list):
                errors = [errors]
            
            # Truncate long messages
            for error in errors:
                if error.get("Message") and len(error["Message"]) > 200:
                    error["Message"] = error["Message"][:200] + "..."
            
            return json.dumps({
                "count": len(errors),
                "period": "last 24 hours",
                "errors": errors
            }, indent=2)
        
        return json.dumps({
            "count": 0,
            "period": "last 24 hours",
            "errors": [],
            "message": "No errors found in the last 24 hours"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def check_disk_health() -> str:
    """
    Check disk drive health status using SMART data
    
    Returns:
    - drives: List of drives with health status
    
    Use when: User asks about disk health, drive failing, SMART status
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size, HealthStatus, OperationalStatus | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            drives = json.loads(result.stdout)
            if not isinstance(drives, list):
                drives = [drives]
            
            formatted_drives = []
            for drive in drives:
                size_gb = round(drive.get("Size", 0) / 1024 / 1024 / 1024, 1) if drive.get("Size") else 0
                formatted_drives.append({
                    "name": drive.get("FriendlyName", "Unknown"),
                    "type": drive.get("MediaType", "Unknown"),
                    "size_gb": size_gb,
                    "health": drive.get("HealthStatus", "Unknown"),
                    "status": drive.get("OperationalStatus", "Unknown")
                })
            
            all_healthy = all(d["health"] == "Healthy" for d in formatted_drives)
            
            return json.dumps({
                "overall_status": "healthy" if all_healthy else "warning",
                "drive_count": len(formatted_drives),
                "drives": formatted_drives
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_bluetooth_devices() -> str:
    """
    Get connected Bluetooth devices
    
    Returns:
    - devices: List of Bluetooth devices
    - bluetooth_enabled: Whether Bluetooth is on
    
    Use when: User asks about Bluetooth, paired devices, wireless devices
    """
    try:
        # Check if Bluetooth is enabled
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
             "Where-Object {$_.Status -eq 'OK'} | "
             "Select-Object FriendlyName, Status, InstanceId | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        devices = []
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                data = [data]
            
            for device in data:
                name = device.get("FriendlyName", "Unknown")
                # Skip generic Bluetooth adapters, show actual devices
                if "Radio" not in name and "Adapter" not in name:
                    devices.append({
                        "name": name,
                        "status": device.get("Status", "Unknown"),
                        "connected": device.get("Status") == "OK"
                    })
        
        # Also get paired/connected audio devices
        result2 = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | "
             "Where-Object {$_.FriendlyName -like '*Bluetooth*' -or $_.FriendlyName -like '*Wireless*'} | "
             "Select-Object FriendlyName, Status | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result2.returncode == 0 and result2.stdout.strip():
            try:
                audio = json.loads(result2.stdout)
                if not isinstance(audio, list):
                    audio = [audio]
                for device in audio:
                    devices.append({
                        "name": device.get("FriendlyName", "Unknown"),
                        "type": "audio",
                        "status": device.get("Status", "Unknown"),
                        "connected": device.get("Status") == "OK"
                    })
            except:
                pass
        
        return json.dumps({
            "device_count": len(devices),
            "devices": devices
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# MCP TOOL DEFINITIONS
# ============================================================================

MCP_TOOL_DEFINITIONS = [
    {
        "name": "get-cpu-usage",
        "description": "Get current CPU usage and top CPU-consuming processes. Use when user asks about CPU, processor usage, or performance.",
        "function": get_cpu_usage
    },
    {
        "name": "get-memory-usage",
        "description": "Get memory/RAM usage statistics and top memory-consuming processes. Use when user asks about memory, RAM, or why system is slow.",
        "function": get_memory_usage
    },
    {
        "name": "get-disk-usage",
        "description": "Get disk space information for all drives. Use when user asks about storage, disk space, or 'running out of space'.",
        "function": get_disk_usage
    },
    {
        "name": "get-disk-io",
        "description": "Get disk I/O statistics and processes performing heavy disk operations. Use when disk activity is high or system feels sluggish.",
        "function": get_disk_io
    },
    {
        "name": "get-network-status",
        "description": "Get network adapter status and internet connectivity. Use when user asks about network, WiFi, or internet connection.",
        "function": get_network_status
    },
    {
        "name": "get-battery-info",
        "description": "Get battery status for laptops. Use when user asks about battery percentage or time remaining.",
        "function": get_battery_info
    },
    {
        "name": "get-process-info",
        "description": "Get detailed information about a specific process by name. Use when user asks 'what is X process' or 'why is X using resources'.",
        "function": get_process_info,
        "parameters": {
            "type": "object",
            "properties": {
                "process_name": {
                    "type": "string",
                    "description": "Name of the process to look up (e.g., 'chrome.exe', 'python')"
                }
            },
            "required": ["process_name"]
        }
    },
    {
        "name": "kill-process",
        "description": "Terminate a process by PID. WARNING: Always confirm with user before calling. Use only when user explicitly asks to close/kill a process.",
        "function": kill_process,
        "parameters": {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID to terminate"
                }
            },
            "required": ["pid"]
        }
    },
    {
        "name": "check-windows-defender",
        "description": "Check Windows Defender antivirus status. Use when user asks about virus protection or Defender.",
        "function": check_windows_defender
    },
    {
        "name": "check-firewall",
        "description": "Check Windows Firewall status for all network profiles. Use when user asks about firewall or network security.",
        "function": check_firewall
    },
    {
        "name": "check-windows-updates",
        "description": "Check for pending Windows updates including critical security patches. Use when user asks if system is up to date.",
        "function": check_windows_updates
    },
    {
        "name": "flush-dns",
        "description": "Flush DNS cache to resolve DNS issues. Use when user reports websites not loading or DNS problems.",
        "function": flush_dns
    },
    {
        "name": "renew-ip",
        "description": "Release and renew DHCP IP address. WARNING: Briefly disconnects network. Use for IP conflicts or network issues.",
        "function": renew_ip
    },
    {
        "name": "test-internet",
        "description": "Test internet connectivity by pinging reliable servers and testing DNS. Use when user asks 'is my internet working'.",
        "function": test_internet_connection
    },
    {
        "name": "find-large-files",
        "description": "Find large files in a directory to identify what's taking up disk space. Use when user asks about disk space usage.",
        "function": find_large_files,
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to search (e.g., 'C:\\Users\\Username\\Downloads')"
                },
                "min_size_mb": {
                    "type": "integer",
                    "description": "Minimum file size in MB (omit for default of 100)"
                }
            },
            "required": ["directory"]
        }
    },
    # ------------------------------------------------------------------
    # HARDWARE & SYSTEM INFO TOOLS
    # ------------------------------------------------------------------
    {
        "name": "get-system-info",
        "description": "Get comprehensive system information including Windows version, processor, RAM, uptime. Use when user asks 'what are my specs', 'system info', 'PC details'.",
        "function": get_system_info
    },
    {
        "name": "get-gpu-usage",
        "description": "Get GPU information and usage (supports NVIDIA with temperature/utilization, and integrated graphics). Use when user asks about graphics card, GPU, video memory.",
        "function": get_gpu_usage
    },
    {
        "name": "get-screen-info",
        "description": "Get display/monitor information including resolution, refresh rate, and number of monitors. Use when user asks about screen, resolution, display settings.",
        "function": get_screen_info
    },
    # ------------------------------------------------------------------
    # TROUBLESHOOTING TOOLS
    # ------------------------------------------------------------------
    {
        "name": "get-recent-errors",
        "description": "Get recent Windows Event Log errors from the last 24 hours. Use when user reports issues, crashes, or wants to diagnose problems.",
        "function": get_recent_errors
    },
    {
        "name": "check-disk-health",
        "description": "Check disk drive health status using SMART data. Use when user asks about disk health, drive status, or suspects a failing drive.",
        "function": check_disk_health
    },
    {
        "name": "get-bluetooth-devices",
        "description": "Get connected Bluetooth devices including audio devices. Use when user asks about Bluetooth, paired devices, wireless headphones.",
        "function": get_bluetooth_devices
    }
]