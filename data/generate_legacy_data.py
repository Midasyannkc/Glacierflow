"""
Synthetic legacy enterprise data, shaped to mirror what actually gets
exported from an on-prem SQL Server/Oracle system ahead of an AWS DMS
migration: customers, orders, order line items, and products, with the
kind of light schema drift (a few legacy column names, inconsistent
null handling) that's realistic to encounter in a real migration
source, not a clean synthetic dataset.

Run: python generate_legacy_data.py
Output: legacy_customers.csv, legacy_orders.csv, legacy_order_items.csv,
        legacy_products.csv
"""
import csv
import random
from datetime import date, timedelta

random.seed(77)

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
PRODUCT_CATEGORIES = ["Electronics", "Home Goods", "Apparel", "Sporting Goods", "Office Supplies"]

N_CUSTOMERS = 5000
N_PRODUCTS = 800
N_ORDERS = 22000
START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 8, 25)


def random_date():
    span = (END_DATE - START_DATE).days
    return START_DATE + timedelta(days=random.randint(0, span))


def build_customers():
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        rows.append({
            "CUST_ID": i,               # legacy naming convention, all-caps, underscore
            "cust_name": f"Customer {i}",
            "region": random.choice(REGIONS),
            # legacy nullability quirk: ~4% of records missing signup date,
            # a realistic migration data-quality issue DMS validation has
            # to surface, not hide
            "signup_dt": random_date().isoformat() if random.random() > 0.04 else "",
        })
    return rows


def build_products():
    rows = []
    for i in range(1, N_PRODUCTS + 1):
        category = random.choice(PRODUCT_CATEGORIES)
        rows.append({
            "PROD_ID": i,
            "prod_name": f"{category} Item {i}",
            "category": category,
            "unit_cost": round(random.uniform(5, 300), 2),
        })
    return rows


def build_orders_and_items(customers, products):
    orders = []
    items = []
    item_id = 1
    for order_id in range(1, N_ORDERS + 1):
        cust = random.choice(customers)
        order_date = random_date()
        status = random.choices(
            ["completed", "completed", "completed", "cancelled", "returned"],
            weights=[70, 15, 5, 5, 5],
        )[0]

        orders.append({
            "ORDER_ID": order_id,
            "CUST_ID": cust["CUST_ID"],
            "order_dt": order_date.isoformat(),
            "region": cust["region"],
            "status": status,
        })

        n_items = random.randint(1, 5)
        chosen_products = random.sample(products, k=min(n_items, len(products)))
        for prod in chosen_products:
            qty = random.randint(1, 4)
            unit_price = round(prod["unit_cost"] * random.uniform(1.3, 1.9), 2)
            items.append({
                "ITEM_ID": item_id,
                "ORDER_ID": order_id,
                "PROD_ID": prod["PROD_ID"],
                "qty": qty,
                "unit_price": unit_price,
            })
            item_id += 1
    return orders, items


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    customers = build_customers()
    products = build_products()
    orders, items = build_orders_and_items(customers, products)

    write_csv(customers, "legacy_customers.csv")
    write_csv(products, "legacy_products.csv")
    write_csv(orders, "legacy_orders.csv")
    write_csv(items, "legacy_order_items.csv")

    print(f"legacy_customers.csv: {len(customers)} rows")
    print(f"legacy_products.csv: {len(products)} rows")
    print(f"legacy_orders.csv: {len(orders)} rows")
    print(f"legacy_order_items.csv: {len(items)} rows")


if __name__ == "__main__":
    main()
