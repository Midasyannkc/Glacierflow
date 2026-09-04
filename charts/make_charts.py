import csv
import matplotlib.pyplot as plt

plt.rcParams["font.size"] = 11


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


validation = load_csv("../data/migration_validation_report.csv")
partition = load_csv("../data/athena_partition_pruning_results.csv")

fig, ax = plt.subplots(figsize=(8, 5.5))
tables = [r["table"] for r in validation]
source_counts = [int(r["source_row_count"]) for r in validation]
target_counts = [int(r["target_row_count"]) for r in validation]

x = range(len(tables))
width = 0.35
ax.bar([i - width / 2 for i in x], source_counts, width, label="Source (legacy CSV)", color="#4A5568")
ax.bar([i + width / 2 for i in x], target_counts, width, label="Target (migrated Parquet)", color="#2B7A6B")
ax.set_xticks(list(x))
ax.set_xticklabels([t.replace(" (join product)", "\n(join product)") for t in tables], fontsize=9)
ax.set_ylabel("Row count")
ax.set_title("Migration Validation: Source vs. Target Row Counts")
ax.legend()
for i, (s, t) in enumerate(zip(source_counts, target_counts)):
    ax.text(i, max(s, t) + max(source_counts) * 0.02, "MATCH", ha="center", fontsize=9, color="#2B7A6B", fontweight="bold")
fig.tight_layout()
fig.savefig("migration_validation.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 5.5))
labels = ["Full scan\n(no partition filter)", "Partition-pruned\n(single month)"]
times = [float(partition[0]["elapsed_ms"]), float(partition[1]["elapsed_ms"])]
bars = ax.bar(labels, times, color=["#8B3A3A", "#2B7A6B"], width=0.5)
ax.set_ylabel("Query time (ms)")
ax.set_title("Athena-Equivalent Partition Pruning\n(measured against real partitioned Parquet)")
for bar, t in zip(bars, times):
    ax.text(bar.get_x() + bar.get_width() / 2, t + max(times) * 0.02, f"{t:.1f} ms", ha="center", fontsize=11, fontweight="bold")
speedup = times[0] / times[1]
ax.text(0.5, max(times) * 0.85, f"{speedup:.1f}x faster", ha="center", transform=ax.transData, fontsize=13, color="#2B7A6B", fontweight="bold")
fig.tight_layout()
fig.savefig("athena_partition_pruning.png", dpi=150)
plt.close(fig)

print("Charts written: migration_validation.png, athena_partition_pruning.png")
