"""Composite keys, explicit null policy, and exact native/JSON inspection."""

import json

import pandas as pd

from framebond import DataModel

customers = pd.DataFrame({"tenant": ["A", "B"], "id": [1, 1]})
orders = pd.DataFrame(
    {"tenant": ["A", "B", "C", "C"], "customer": [1, None, 9, 9]},
    index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-03"]),
)
model = DataModel().add_table("customers", customers, primary_key=["tenant", "id"])
model.add_table("orders", orders)
model.add_relation(
    ("orders", ["tenant", "customer"]),
    ("customers", ["tenant", "id"]),
    nulls="forbid",
    name="customer_reference",
)
report = model.validate()
assert report.relations[0].null_rows == 1
assert report.relations[0].orphan_rows == 2
assert report.relations[0].missing_keys == 1
encoded = report.to_json()
assert json.loads(encoded)["valid"] is False
print(report.explain())
print(encoded)
