# Cookbook: framebond

Three common operational problems, with complete Python code and asserted outcomes. The records are **synthetic fixtures modeled on real workflows**, not measurements from a business or real customer data.

Install `python -m pip install "framebond==0.2.0"`. From a checkout, run all three with `python examples/cookbook.py`.

<a id="find-bad-order-records"></a>
## Quarantine bad orders from an upload

**Problem.** A repeated CSV index label cannot uniquely identify a bad record. The FK also has an explicit null policy.

**Expected result.** Find orphan position 1 with `.iloc`, identify order 11, and report the null FK separately under nulls="forbid".

Copy the complete block into a fresh Python file and run it:

```python
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


print(find_bad_order_records())
```

**Apply it to your data.** A row can have more than one issue code. Deduplicate source positions when building a quarantine file.

<a id="validate-product-tags"></a>
## Validate a many-to-many product/tag mapping

**Problem.** Products can have many tags and tags can belong to many products. A retired tag remains in the mapping export.

**Expected result.** Use a junction table with two foreign keys. The product relation passes and the tag relation reports one orphan.

Copy the complete block into a fresh Python file and run it:

```python
import json
import pandas as pd
from framebond import DataModel


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


print(validate_product_tags())
```

**Apply it to your data.** This checks FK membership; it does not require every product or tag to participate in a link.

<a id="preserve-exact-external-ids"></a>
## Keep large imported identifiers exact

**Problem.** Adjacent external integer identifiers exceed 2**53 and appear beside a null value.

**Expected result.** Construct object-backed identifiers, identify the adjacent orphan exactly and preserve its integer value in JSON.

Copy the complete block into a fresh Python file and run it:

```python
import json
import pandas as pd
from framebond import DataModel


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


print(preserve_exact_external_ids())
```

**Apply it to your data.** Precision lost during CSV or DataFrame parsing cannot be recovered. Set input dtypes before validation.

[API details and error policies](api.md) · [Comparison with primitives](comparison.md) · [Benchmark evidence](../benchmarks/RESULTS.md)
