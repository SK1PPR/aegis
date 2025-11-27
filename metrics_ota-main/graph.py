# Let's analyze why most metrics showed "No data found" and improve the script
# Based on the text file analysis, let's identify the exact field names that exist

# Parse the field mappings from the text file data
field_mappings = {
    'TUF': {
        'cpu_usage': ['cpu_pct'],
        'memory_usage': ['mem_mb'], 
        'duration': ['duration_sec'],
        'latency': ['latency_ms'],
        'download_count': ['download_count'],
        'download_success': ['download_success'],
        'updates_attempted': ['updates_attempted'],
        'updates_successful': ['updates_successful']
    },
    'Blockchain OTA': {
        'cpu_usage': ['cpu_pct'],
        'memory_usage': ['mem_mb'],
        'duration': ['duration_sec', 'seconds'],
        'mining_time': ['mining_time'],
        'blockchain_difficulty': ['blockchain_difficulty'],
        'deploy_attempts': ['deploy_attempts'],
        'deploy_success': ['deploy_success']
    },
    'SWUpdate': {
        'cpu_usage': ['cpu_percent'],
        'memory_usage': ['memory_mb'],
        'duration': ['duration_sec'],
        'disk_usage': ['disk_percent', 'disk_used_gb'],
        'updates_attempted': ['updates_attempted'],
        'updates_failed': ['updates_failed']
    },
    'RAUC': {
        'cpu_usage': ['cpu_pct'],
        'memory_usage': ['mem_mb'],
        'duration': ['duration_sec'],
        'disk_usage': ['disk_used_gb', 'disk_free_gb'],
        'updates_attempted': ['updates_attempted'],
        'updates_successful': ['updates_successful'],
        'install_bundle_count': ['install_bundle_count']
    },
    'Balena': {
        'cpu_usage': ['cpu_pct'],
        'memory_usage': ['mem_mb'],
        'duration': ['duration_sec'],
        'balena_push_count': ['balena_push_count'],
        'balena_push_error': ['balena_push_error']
    },
    'Legacy OTA': {
        'cpu_usage': ['cpu_percent'],
        'memory_usage': ['memory_used_mb'],
        'duration': ['duration_sec'],
        'latency': ['latency_ms'],
        'download_speed': ['download_speed_mbps'],
        'bytes_used': ['bytes_used'],
        'updates_attempted': ['updates_attempted']
    },
    'Uptane': {
        'cpu_usage': ['cpu_pct'],
        'memory_usage': ['mem_mb'],
        'duration': ['duration_sec'],
        'latency': ['latency_ms'],
        'manifests': ['manifests']
    },
    'HawkBit': {
        'cpu_usage': ['cpu_percent'],
        'memory_usage': ['memory_used_mb'],
        'duration': ['duration_sec'],
        'latency': ['latency_ms'],
        'bandwidth': ['bandwidth_mbps'],
        'bytes_used': ['bytes_used'],
        'updates_attempted': ['updates_attempted'],
        'updates_successful': ['updates_successful'],
        'polling_cycles': ['polling_cycles']
    },
    'Modern OTA': {
        'cpu_usage': ['cpu_percent'],
        'memory_usage': ['memory_used_mb'],
        'duration': ['duration_sec'],
        'latency': ['latency_ms'],
        'download_speed': ['download_speed_mbps'],
        'bytes_used': ['bytes_used'],
        'updates_attempted': ['updates_attempted'],
        'updates_successful': ['updates_successful'],
        'delta_ratio': ['delta_ratio'],
        'bandwidth_savings_percent': ['bandwidth_savings_percent']
    },
    'MQTT OTA': {
        'cpu_usage': ['cpu_pct'],
        'memory_usage': ['mem_mb'],
        'duration': ['duration_sec'],
        'deploy_attempts': ['deploy_attempts'],
        'deploy_success': ['deploy_success'],
        'mqtt_messages': ['mqtt_messages'],
        'firmware_downloads': ['firmware_downloads']
    }
}

print("ISSUE ANALYSIS:")
print("The script found 'No data found' because it was looking for generic field names")
print("But each OTA system uses different field names for similar metrics")
print("\nSOLUTION:")
print("We need to update the field mappings in the script to match the actual field names")
print("\nFor example:")
print("- TUF uses 'cpu_pct' while Legacy OTA uses 'cpu_percent'") 
print("- TUF uses 'mem_mb' while HawkBit uses 'memory_used_mb'")
print("- Some systems have 'duration_sec', others have 'seconds'")

print(f"\nFOUND MAPPINGS FOR {len(field_mappings)} SYSTEMS:")
for system, fields in field_mappings.items():
    print(f"  {system}: {len(fields)} metrics mapped")