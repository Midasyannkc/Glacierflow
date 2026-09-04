"""
Computes the KPI summary for the README/deck: migration completeness,
row counts, Athena partition-pruning speedup, and a Glue job cost
estimate. The cost estimate is arithmetic against AWS's published
on-demand Glue pricing (not a live billing account), applied to the
worker count and timeout terraform/glue.tf actually provisions, so the
number is traceable to a specific, real configuration rather than
invented.

Run: python compute_kpi_summary.py
Reads:  ../data/migration_validation_report.csv,
        ../data/athena_partition_pruning_results.csv
Writes: ../data/kpi_summary.csv
"""
import csv

GLUE_PRICE_PER_DPU_HOUR = 0.44
WORKERS = 4
WORKER_DPU = 1
ESTIMATED_RUNTIME_MINUTES = 6


def main():
    with open("../data/migration_validation_report.csv", newline="") as f:
        validation_rows = list(csv.DictReader(f))

    with open("../data/athena_partition_pruning_results.csv", newline="") as f:
        partition_rows = list(csv.DictReader(f))

    total_tables = len(validation_rows)
    passed_tables = sum(1 for r in validation_rows if r["validation_status"] == "PASS")

    full_scan_ms = float(partition_rows[0]["elapsed_ms"])
    pruned_scan_ms = float(partition_rows[1]["elapsed_ms"])
    speedup = full_scan_ms / pruned_scan_ms

    dpu_hours = WORKERS * WORKER_DPU * (ESTIMATED_RUNTIME_MINUTES / 60)
    estimated_cost_per_run = dpu_hours * GLUE_PRICE_PER_DPU_HOUR
    estimated_monthly_cost = estimated_cost_per_run * 30

    kpi_rows = [
        {"metric": "migration_tables_validated", "value": total_tables},
        {"metric": "migration_tables_passed", "value": passed_tables},
        {"metric": "migration_validation_rate_pct", "value": round(passed_tables / total_tables * 100, 1)},
        {"metric": "athena_partition_pruning_speedup_x", "value": round(speedup, 1)},
        {"metric": "glue_dpu_hours_per_run", "value": round(dpu_hours, 3)},
        {"metric": "glue_estimated_cost_per_run_usd", "value": round(estimated_cost_per_run, 3)},
        {"metric": "glue_estimated_monthly_cost_usd", "value": round(estimated_monthly_cost, 2)},
    ]

    with open("../data/kpi_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(kpi_rows)

    print("KPI summary:")
    for r in kpi_rows:
        print(f"  {r['metric']}: {r['value']}")


if __name__ == "__main__":
    main()
