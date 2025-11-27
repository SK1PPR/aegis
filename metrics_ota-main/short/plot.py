import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Create output directory
output_dir = './ablation_figures'
os.makedirs(output_dir, exist_ok=True)

# Set style and fonts - ENHANCED
plt.rcParams.update({
    'font.size': 28,
    'axes.titlesize': 0,  # NO TITLE
    'axes.labelsize': 32,  # LARGER AXIS LABELS
    'xtick.labelsize': 22,
    'ytick.labelsize': 26,  # MUCH LARGER Y-AXIS LABELS
    'legend.fontsize': 20,
    'axes.linewidth': 2,
    'xtick.major.width': 2,
    'xtick.major.size': 8,
    'ytick.major.width': 2,
    'ytick.major.size': 8,
})
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")

# ============================================================================
# ABLATION STUDY - RELIABILITY METRICS
# ============================================================================

# Graph 1: Success Rate vs Component Removal
fig, ax = plt.subplots(figsize=(14, 9))
components = ['COOM\n(Full)', 'w/o Container\nOrchestration', 'w/o Atomic\nValidation', 'w/o Multi-ECU\nSync', 'w/o Rollback\nMechanism']
success_rates = [96, 88, 89, 84, 87]
colors = ['#2ecc71', '#e74c3c', '#e67e22', '#e74c3c', '#c0392b']

bars = ax.bar(components, success_rates, color=colors, edgecolor='black', linewidth=3, alpha=0.9, width=0.65)
ax.set_ylabel('Success Rate (%)', fontsize=32, fontweight='bold', labelpad=15)
ax.set_ylim([75, 100])
ax.grid(axis='y', alpha=0.4, linestyle='--', linewidth=1.5)

for i, bar in enumerate(bars):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
            f'{int(height)}%',
            ha='center', va='bottom', fontsize=26, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{output_dir}/01a_component_success_rate.pdf', dpi=2400, bbox_inches='tight', facecolor='white')
plt.close()

# Graph 2: Rollback Rate vs Component Removal
fig, ax = plt.subplots(figsize=(14, 9))
configs = ['COOM\n(Full)', 'w/o Atomic\nRollback', 'w/o Validation\nPipeline', 'w/o Failure\nRecovery', 'w/o State\nManagement']
rollback_rates = [2, 8, 7, 12, 9]
colors = ['#27ae60', '#c0392b', '#e74c3c', '#e74c3c', '#c0392b']

bars = ax.bar(configs, rollback_rates, color=colors, edgecolor='black', linewidth=3, alpha=0.9, width=0.65)
ax.set_ylabel('Rollback Rate (%)', fontsize=32, fontweight='bold', labelpad=15)
ax.set_ylim([0, 15])
ax.grid(axis='y', alpha=0.4, linestyle='--', linewidth=1.5)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.3,
            f'{int(height)}%',
            ha='center', va='bottom', fontsize=26, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{output_dir}/01b_component_rollback_rate.pdf', dpi=2400, bbox_inches='tight', facecolor='white')
plt.close()

# Graph 3: Operation Duration vs Component Removal
fig, ax = plt.subplots(figsize=(14, 9))
duration_configs = ['COOM\n(Full)', 'w/o Start-First\nStrategy', 'w/o Container\nOptimization', 'w/o Network\nManagement', 'w/o Resource\nScheduling']
durations = [1.4, 2.1, 2.0, 1.8, 2.3]
colors = ['#16a085', '#e74c3c', '#e67e22', '#e67e22', '#c0392b']

bars = ax.bar(duration_configs, durations, color=colors, edgecolor='black', linewidth=3, alpha=0.9, width=0.65)
ax.set_ylabel('Operation Duration (s)', fontsize=32, fontweight='bold', labelpad=15)
ax.set_ylim([0, 2.8])
ax.grid(axis='y', alpha=0.4, linestyle='--', linewidth=1.5)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.08,
            f'{height:.1f}s',
            ha='center', va='bottom', fontsize=26, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{output_dir}/01c_component_duration.pdf', dpi=2400, bbox_inches='tight', facecolor='white')
plt.close()

# ============================================================================
# ROBUSTNESS ANALYSIS - OPERATIONAL CONDITIONS
# ============================================================================

# Graph 4: Network Latency Robustness
fig, ax = plt.subplots(figsize=(14, 9))
latency_conditions = ['0-50ms\n(Ideal)', '50-150ms\n(Good)', '150-300ms\n(Fair)', '300-500ms\n(Poor)', '>500ms\n(Degraded)']
success_latency = [96, 94, 91, 87, 82]

bars = ax.bar(latency_conditions, success_latency, color='#3498db', edgecolor='black', linewidth=3, alpha=0.9, width=0.6)
ax.set_ylabel('Success Rate (%)', fontsize=32, fontweight='bold', labelpad=15)
ax.set_ylim([75, 100])
ax.grid(axis='y', alpha=0.4, linestyle='--', linewidth=1.5)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
            f'{int(height)}%',
            ha='center', va='bottom', fontsize=26, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{output_dir}/02a_network_latency.pdf', dpi=2400, bbox_inches='tight', facecolor='white')
plt.close()

# Graph 5: Fleet Size Scalability
fig, ax = plt.subplots(figsize=(14, 9))
fleet_sizes = ['100\nDevices', '500\nDevices', '1K\nDevices', '5K\nDevices', '10K\nDevices']
throughput_fleet = [7.8, 7.6, 7.4, 7.1, 6.8]

bars = ax.bar(fleet_sizes, throughput_fleet, color='#9b59b6', edgecolor='black', linewidth=3, alpha=0.9, width=0.6)
ax.set_ylabel('Throughput (events/s)', fontsize=32, fontweight='bold', labelpad=15)
ax.set_ylim([6, 8.5])
ax.grid(axis='y', alpha=0.4, linestyle='--', linewidth=1.5)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
            f'{height:.2f}',
            ha='center', va='bottom', fontsize=26, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{output_dir}/02b_fleet_scalability.pdf', dpi=2400, bbox_inches='tight', facecolor='white')
plt.close()

# Graph 6: Fault Recovery under Adverse Scenarios
fig, ax = plt.subplots(figsize=(14, 9))
fault_scenarios = ['Baseline\n(No Fault)', 'ECU Comm\nFailure', 'Image\nCorruption', 'Network\nInterruption', 'Concurrent\nUpdates']
recovery_rates = [96, 92, 94, 89, 87]
colors_faults = ['#27ae60', '#f39c12', '#e67e22', '#c0392b', '#e74c3c']

bars = ax.bar(fault_scenarios, recovery_rates, color=colors_faults, edgecolor='black', linewidth=3, alpha=0.9, width=0.65)
ax.set_ylabel('Recovery Success (%)', fontsize=32, fontweight='bold', labelpad=15)
ax.set_ylim([80, 100])
ax.grid(axis='y', alpha=0.4, linestyle='--', linewidth=1.5)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
            f'{int(height)}%',
            ha='center', va='bottom', fontsize=26, fontweight='bold')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{output_dir}/02c_fault_recovery.pdf', dpi=2400, bbox_inches='tight', facecolor='white')
plt.close()

print("✓ All enhanced ablation and robustness figures generated!")
print(f"✓ Output: {output_dir}/")
print("✓ Files generated (2400 DPI, no titles, large labels):")
print("  - 01a_component_success_rate.pdf")
print("  - 01b_component_rollback_rate.pdf")
print("  - 01c_component_duration.pdf")
print("  - 02a_network_latency.pdf")
print("  - 02b_fleet_scalability.pdf")
print("  - 02c_fault_recovery.pdf")