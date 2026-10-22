"""Same orphan positions for integer keys; model adds reusable constraints."""

import pandas as pd

from framebond import DataModel


def baseline(customers, orders):
    key = orders["customer_id"]
    orphans = key.notna() & ~key.isin(customers["id"].dropna())
    return tuple(position for position, orphan in enumerate(orphans) if orphan)


def library(customers, orders):
    model = DataModel().add_table("customers", customers, primary_key="id")
    model.add_table("orders", orders, primary_key="id")
    model.add_relation("orders.customer_id", "customers.id")
    report = model.validate()
    return tuple(report.issues(code="foreign_key_orphan")["row_position"])


if __name__ == "__main__":
    customers = pd.DataFrame({"id": [1, 2]})
    orders = pd.DataFrame({"id": [10, 11, 12], "customer_id": [1, 9, None]})
    assert baseline(customers, orders) == library(customers, orders) == (1,)
    print("Both identify original position 1; the null FK is exempt by policy.")
