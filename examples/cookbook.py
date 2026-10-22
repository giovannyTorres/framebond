"""Three operational integrity checks, with deterministic synthetic fixtures."""

import json

import pandas as pd

from framebond import DataModel


def find_bad_order_records():
    customers = pd.DataFrame({"id": [1, 2]})
    orders = pd.DataFrame(
        {"id": [10, 11, 12], "customer_id": [1, 9, None]}, index=["upload", "upload", "upload"]
    )
    model = DataModel().add_table("customers", customers, primary_key="id")
    model.add_table("orders", orders, primary_key="id")
    model.add_relation("orders.customer_id", "customers.id", nulls="forbid")
    report = model.validate()
    assert report.relations[0].orphan_rows == 1
    assert report.relations[0].null_rows == 1
    positions = report.issues(code="foreign_key_orphan")["row_position"].tolist()
    assert positions == [1]
    assert orders.iloc[positions]["id"].tolist() == [11]
    return report.explain()


def validate_product_tags():
    products = pd.DataFrame({"id": [1, 2]})
    tags = pd.DataFrame({"id": ["sale", "new"]})
    links = pd.DataFrame({"product_id": [1, 2], "tag_id": ["sale", "retired"]})
    model = DataModel().add_table("products", products, primary_key="id")
    model.add_table("tags", tags, primary_key="id").add_table("links", links)
    model.add_relation("links.product_id", "products.id")
    model.add_relation("links.tag_id", "tags.id")
    report = model.validate()
    assert [relation.orphan_rows for relation in report.relations] == [0, 1]
    return report.explain()


def preserve_exact_external_ids():
    huge = 2**53 + 1
    parent = pd.DataFrame({"id": pd.Series([huge], dtype=object)})
    child = pd.DataFrame({"customer": pd.Series([huge, huge + 1, None], dtype=object)})
    model = DataModel().add_table("customers", parent, primary_key="id").add_table("orders", child)
    model.add_relation("orders.customer", "customers.id")
    report = model.validate()
    assert report.issues(code="foreign_key_orphan").iloc[0]["key"] == (huge + 1,)
    encoded = report.to_json()
    assert str(huge + 1) in encoded
    assert json.loads(encoded)["valid"] is False
    return encoded


if __name__ == "__main__":
    for recipe in (find_bad_order_records, validate_product_tags, preserve_exact_external_ids):
        print(recipe.__name__, recipe(), sep="\n")
