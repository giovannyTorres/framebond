import json
from datetime import date, time, timedelta
from decimal import Decimal
from uuid import UUID

import numpy as np
import pandas as pd
import pytest

from framebond import DataModel, ModelError, PandasBackend


def test_primary_keys_counts_issues_and_explanation():
    frame = pd.DataFrame(
        {"id": [1, 2, 1, None, 2], "payload": ["a", "b", "c", "d", "e"]}, index=[8, 8, 3, 3, 8]
    )
    report = DataModel().add_table("table", frame, primary_key="id").validate()
    result = report.tables[0]
    assert result.rows == 5
    assert not result.primary_key_valid
    assert result.null_rows == 1
    assert result.duplicate_rows == 4
    assert result.duplicate_keys == 2
    assert report.issues(code="primary_key_duplicate")["row_position"].tolist() == [0, 1, 2, 4]
    assert report.issues(code="primary_key_null")["index"].tolist() == [3]
    assert "Overall: INVALID" in report.explain()
    assert "Primary key INVALID" in report.explain()
    assert report.issues(table="not-present").empty
    assert report.issues(relation="not-present").empty


def test_valid_model_undeclared_primary_key_and_repeated_runs():
    customers = pd.DataFrame({"id": [1, 2]})
    orders = pd.DataFrame({"id": [10, 11], "customer": [1, 2]})
    model = DataModel().add_table("customers", customers, primary_key="id")
    model.add_table("orders", orders).add_relation("orders.customer", "customers.id")
    report = model.validate()
    assert report.valid
    assert report.tables[1].primary_key_valid is None
    assert report.issues().empty
    assert "NOT DECLARED" in report.explain()
    assert "Foreign key VALID" in report.explain()
    assert report.to_dict() == model.validate().to_dict()
    assert json.loads(report.to_json(indent=None))["valid"] is True
    assert DataModel().validate().valid


def test_one_to_one_duplicates_and_default_relationship():
    child = pd.DataFrame({"id": [1, 1, None]})
    parent = pd.DataFrame({"id": [1]})
    model = DataModel().add_table("c", child).add_table("p", parent)
    model.add_relation("c.id", "p.id", name="ordinary")
    model.add_relation("c.id", "p.id", name="strict", nulls="forbid", relationship="one_to_one")
    report = model.validate()
    assert report.relations[0].valid
    assert report.relations[0].observed_relationship == "many_to_one"
    assert not report.relations[1].valid
    assert report.issues(relation="strict", code="relation_child_duplicate")[
        "row_position"
    ].tolist() == [0, 1]
    assert report.issues(relation="strict", code="foreign_key_null")["row_position"].tolist() == [2]


def test_type_equality_and_container_rejection():
    model = DataModel().add_table("c", pd.DataFrame({"id": pd.Series([1, "1"], dtype=object)}))
    model.add_table("p", pd.DataFrame({"id": [1.0]})).add_relation("c.id", "p.id")
    report = model.validate()
    assert report.relations[0].orphan_rows == 1
    assert report.issues(code="foreign_key_orphan")["key"].tolist() == [("1",)]
    with pytest.raises(ModelError, match="scalar"):
        DataModel().add_table("bad", pd.DataFrame({"id": [[1]]}), primary_key="id")
    # A NumPy scalar can still be unhashable (structured writable void scalar).
    unhashable_scalar = np.array([(1,)], dtype=[("field", "i4")])[0]
    with pytest.raises(ModelError, match="Unhashable"):
        PandasBackend().index(
            pd.DataFrame({"id": pd.Series([unhashable_scalar], dtype=object)}), ("id",)
        )


def test_backend_counts_and_original_key_positions():
    big = 2**53 + 1
    index = PandasBackend().index(
        pd.DataFrame({"id": pd.Series([big, None, big, big - 1], dtype=object)}), ("id",)
    )
    assert index.keys == ((big,), (None,), (big,), (big - 1,))
    assert index.null_positions == (1,)
    assert index.positions[(big,)] == (0, 2)
    assert index.duplicate_positions == (0, 2)
    assert index.duplicate_keys == 1


@pytest.mark.parametrize("key", [[], ["id", "id"], ["missing"], [1], 7])
def test_bad_primary_key_configuration(key):
    with pytest.raises(ModelError):
        DataModel().add_table("t", pd.DataFrame({"id": [1]}), primary_key=key)


def test_bad_table_configuration():
    model = DataModel().add_table("t", pd.DataFrame({"id": [1]}))
    for name in ["t", "", "t.x", 7]:
        with pytest.raises(ModelError):
            model.add_table(name, pd.DataFrame({"id": [1]}))
    with pytest.raises(TypeError):
        DataModel().add_table("t", [1])
    with pytest.raises(ModelError, match="unique flat"):
        DataModel().add_table("t", pd.DataFrame([[1, 2]], columns=["id", "id"]))
    with pytest.raises(ModelError, match="unique flat"):
        DataModel().add_table(
            "t", pd.DataFrame([[1]], columns=pd.MultiIndex.from_tuples([("a", "b")]))
        )


@pytest.mark.parametrize(
    "child,parent,kwargs",
    [
        ("no-dot", "p.id", {}),
        ("missing.id", "p.id", {}),
        (("c", ["absent"]), "p.id", {}),
        (("c", ["id", "id"]), "p.id", {}),
        (("c", ["id", "x"]), "p.id", {}),
        ("c.id", "p.id", {"nulls": "match"}),
        ("c.id", "p.id", {"relationship": "many_to_many"}),
        ("c.id", "p.id", {"name": ""}),
        ((1, ["id"]), "p.id", {}),
        (("c", None), "p.id", {}),
    ],
)
def test_bad_relation_configuration(child, parent, kwargs):
    model = DataModel().add_table("c", pd.DataFrame({"id": [1], "x": [2]}))
    model.add_table("p", pd.DataFrame({"id": [1]}))
    with pytest.raises(ModelError):
        model.add_relation(child, parent, **kwargs)


def test_duplicate_relations_rejected_and_failed_registration_atomic():
    model = DataModel().add_table("c", pd.DataFrame({"id": [1], "bad": [[1]]}))
    model.add_table("p", pd.DataFrame({"id": [1]}))
    with pytest.raises(ModelError):
        model.add_relation("c.bad", "p.id", name="bad")
    assert not model.validate().relations
    model.add_relation("c.id", "p.id")
    with pytest.raises(ModelError, match="Relation names"):
        model.add_relation("c.id", "p.id")


def test_json_extended_scalars_are_strict_and_native_issues_stay_original():
    keys = [
        Decimal("1.0000000000000000001"),
        UUID(int=42),
        b"a",
        float("inf"),
        date(2024, 1, 1),
        time(12, 30),
        timedelta(days=1),
        np.bool_(True),
        complex(2, 3),
        None,
        pd.NaT,
        np.datetime64("2024-02-03T12:30:01", "ns"),
        np.timedelta64(123456789, "ns"),
    ]
    frame = pd.DataFrame({"id": pd.Series(keys, dtype=object)})
    frame.index = pd.Index([f"row-{i}" for i in range(len(keys))])
    # Duplicate keys create issues for all original scalars, exercising export.
    frame = pd.concat([frame, frame], ignore_index=True)
    report = DataModel().add_table("t", frame, primary_key="id").validate()
    native = report.issues(code="primary_key_duplicate")
    assert isinstance(native["key"].iloc[0][0], Decimal)
    encoded = report.to_json()
    decoded = json.loads(
        encoded, parse_constant=lambda value: (_ for _ in ()).throw(AssertionError(value))
    )
    assert decoded["valid"] is False
    serialized_keys = [issue["key"][0] for issue in decoded["issues"]]
    assert {"type": "Decimal", "value": "1.0000000000000000001"} in serialized_keys
    assert {"type": "float", "value": "inf"} in serialized_keys
    assert {"type": "bytes", "value": "61"} in serialized_keys
    assert "2024-01-01" in serialized_keys
    assert "12:30:00" in serialized_keys
    assert "2024-02-03T12:30:01" in serialized_keys
    assert {"type": "timedelta64", "value": "P0DT0H0M0.123456789S"} in serialized_keys
    assert None in serialized_keys
