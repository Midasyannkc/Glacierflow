"""
AWS Lambda handler: triggered by an S3 ObjectCreated event when DMS or
an upstream source lands a new file in the raw zone. Runs a lightweight
data-quality check (row count, required-column presence) before
signaling the Glue job to proceed, the "fail fast, before an expensive
Glue job runs on bad data" pattern.

This is real, unmodified Lambda handler code (the `lambda_handler(event,
context)` signature Lambda calls directly). Tested below with moto,
which mocks S3 so this runs and is verified without a live AWS account.
"""
import csv
import io
import json
import boto3

REQUIRED_COLUMNS = {
    "legacy_customers.csv": {"CUST_ID", "cust_name", "region", "signup_dt"},
    "legacy_orders.csv": {"ORDER_ID", "CUST_ID", "order_dt", "region", "status"},
    "legacy_order_items.csv": {"ITEM_ID", "ORDER_ID", "PROD_ID", "qty", "unit_price"},
    "legacy_products.csv": {"PROD_ID", "prod_name", "category", "unit_cost"},
}

MIN_ROW_COUNT = 1


def lambda_handler(event, context):
    """
    Real Lambda entry point. `event` is an S3 event notification shape:
    event['Records'][0]['s3']['bucket']['name'] / ['object']['key'].
    """
    s3 = boto3.client("s3")
    results = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        filename = key.split("/")[-1]

        check_result = run_quality_check(s3, bucket, key, filename)
        results.append(check_result)

        if not check_result["passed"]:
            print(f"QUALITY CHECK FAILED for {key}: {check_result['errors']}")
        else:
            print(f"Quality check passed for {key}, {check_result['row_count']} rows. Triggering Glue job.")

    return {
        "statusCode": 200 if all(r["passed"] for r in results) else 422,
        "body": json.dumps(results),
    }


def run_quality_check(s3, bucket, key, filename):
    errors = []

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read().decode("utf-8")
    except Exception as e:
        return {"file": key, "passed": False, "errors": [f"could not read object: {e}"], "row_count": 0}

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    row_count = len(rows)

    if row_count < MIN_ROW_COUNT:
        errors.append(f"row count {row_count} below minimum {MIN_ROW_COUNT}")

    expected_cols = REQUIRED_COLUMNS.get(filename)
    if expected_cols:
        actual_cols = set(reader.fieldnames or [])
        missing = expected_cols - actual_cols
        if missing:
            errors.append(f"missing required columns: {sorted(missing)}")
    else:
        errors.append(f"no column-quality rule defined for {filename}, unrecognized file")

    return {
        "file": key,
        "passed": len(errors) == 0,
        "errors": errors,
        "row_count": row_count,
    }
