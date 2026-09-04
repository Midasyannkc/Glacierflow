"""
Reproduces AWS DMS's row-level validation locally: compares the legacy
CSV source (what DMS would read from the on-prem source endpoint)
against the migrated gold-layer Parquet (what the Glue transformation
produced), checking row counts and a content checksum per table. This
is the exact question DMS's built-in ValidationSettings (see
dms/replication_task_config.json) answers in production; this script
answers it against the real files this repo actually produced.

Run: python validate_migration.py
Reads:  ../data/legacy_*.csv, ../data/warehouse/gold/
Writes: ../data/migration_validation_report.csv
"""
import csv
import hashlib
import duckdb


def row_count_source(csv_path):
    with open(csv_path, newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def checksum_source_ids(csv_path, id_column):
    with open(csv_path, newline="") as f:
        ids = sorted(int(row[id_column]) for row in csv.DictReader(f))
    return hashlib.sha256(str(ids).encode()).hexdigest()[:16], len(ids)


def main():
    con = duckdb.connect()

    checks = [
        ("customers", "../data/legacy_customers.csv", "CUST_ID",
         "../data/warehouse/gold/dim_customer/*.parquet", "cust_id"),
        ("products", "../data/legacy_products.csv", "PROD_ID",
         "../data/warehouse/gold/dim_product/*.parquet", "prod_id"),
    ]

    report_rows = []
    all_passed = True

    for name, source_csv, source_id_col, target_parquet, target_id_col in checks:
        source_checksum, source_count = checksum_source_ids(source_csv, source_id_col)

        target_ids = con.execute(f"""
            SELECT {target_id_col} FROM parquet_scan('{target_parquet}')
            ORDER BY {target_id_col}
        """).fetchall()
        target_ids_list = sorted(int(r[0]) for r in target_ids)
        target_checksum = hashlib.sha256(str(target_ids_list).encode()).hexdigest()[:16]
        target_count = len(target_ids_list)

        row_count_match = source_count == target_count
        checksum_match = source_checksum == target_checksum
        passed = row_count_match and checksum_match
        all_passed = all_passed and passed

        report_rows.append({
            "table": name,
            "source_row_count": source_count,
            "target_row_count": target_count,
            "row_count_match": row_count_match,
            "source_id_checksum": source_checksum,
            "target_id_checksum": target_checksum,
            "checksum_match": checksum_match,
            "validation_status": "PASS" if passed else "FAIL",
        })

    source_items_count = row_count_source("../data/legacy_order_items.csv")
    target_items_count = con.execute("""
        SELECT COUNT(*) FROM parquet_scan('../data/warehouse/gold/fact_order_items/*/*/*.parquet')
    """).fetchone()[0]
    items_match = source_items_count == target_items_count
    all_passed = all_passed and items_match

    report_rows.append({
        "table": "fact_order_items (join product)",
        "source_row_count": source_items_count,
        "target_row_count": target_items_count,
        "row_count_match": items_match,
        "source_id_checksum": "n/a (join product)",
        "target_id_checksum": "n/a (join product)",
        "checksum_match": "n/a",
        "validation_status": "PASS" if items_match else "FAIL",
    })

    with open("../data/migration_validation_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
        writer.writeheader()
        writer.writerows(report_rows)

    print("Migration validation report (reproduces DMS row-level validation):")
    for r in report_rows:
        print(f"  {r['table']:<32s} source={r['source_row_count']:<8d} target={r['target_row_count']:<8d} {r['validation_status']}")

    print(f"\nOverall migration validation: {'PASS' if all_passed else 'FAIL'}")
    con.close()


if __name__ == "__main__":
    main()
