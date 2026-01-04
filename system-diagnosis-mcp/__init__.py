# System Diagnosis Granular Tools Package
# 15 composable diagnostic tools for the voice agent

from .granular_diagnostic_tools import (
    # Tool definitions
    MCP_TOOL_DEFINITIONS,
    
    # System metrics
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    get_disk_io,
    get_battery_info,
    
    # Network
    get_network_status,
    test_internet_connection,
    flush_dns,
    renew_ip,
    
    # Security
    check_windows_defender,
    check_firewall,
    check_windows_updates,
    
    # Process management
    get_process_info,
    kill_process,
    
    # Cleanup
    find_large_files
)

__all__ = [
    'MCP_TOOL_DEFINITIONS',
    'get_cpu_usage', 'get_memory_usage', 'get_disk_usage', 'get_disk_io', 'get_battery_info',
    'get_network_status', 'test_internet_connection', 'flush_dns', 'renew_ip',
    'check_windows_defender', 'check_firewall', 'check_windows_updates',
    'get_process_info', 'kill_process', 'find_large_files'
]
