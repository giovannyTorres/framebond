"""A runnable customer/order foreign-key validation."""

import pandas as pd

from framebond import DataModel

customers = pd.DataFrame({"id": [1, 2]})
orders = pd.DataFrame({"id": [10, 11, 12], "customer_id": [1, 2, 3]})
model = DataModel().add_table("customers", customers, primary_key="id")
model.add_table("orders", orders, primary_key="id")
model.add_relation("orders.customer_id", "customers.id")
report = model.validate()
assert report.relations[0].orphan_rows == 1
print(report.explain())
print(report.issues(code="foreign_key_orphan"))
