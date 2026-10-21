"""Independent relational-integrity and exact-key regressions."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from framebond import DataModel, ModelError


def test_composite_primary_key_nulls_and_duplicate_positions():
    source = pd.DataFrame(
        {"tenant": ["A", "A", None, "A"], "id": [1, 1, 2, None]}, index=[9, 9, 9, 9]
    )
    original = source.copy(deep=True)
    report = DataModel().add_table("items", source, primary_key=["tenant", "id"]).validate()
    table = report.tables[0]
    assert not report.valid
    assert table.null_rows == 2
    assert table.duplicate_keys == 1
    assert table.duplicate_rows == 2
    issues = report.issues(table="items")
    assert sorted(issues.loc[issues["code"] == "primary_key_null", "row_position"]) == [2, 3]
    assert sorted(issues.loc[issues["code"] == "primary_key_duplicate", "row_position"]) == [0, 1]
    assert issues["index"].tolist() == [9, 9, 9, 9]
    assert_frame_equal(source, original)


@pytest.mark.parametrize("nulls", ["ignore", "forbid"])
def test_composite_match_simple_nulls_and_distinct_orphan_counts(nulls):
    customers = pd.DataFrame({"tenant": ["A"], "id": [1]})
    orders = pd.DataFrame(
        {
            "order": [10, 11, 12, 13, 14],
            "tenant": ["A", None, "A", "A", "A"],
            "customer": [1, 1, None, 9, 9],
        },
        index=[7, 7, 7, 7, 7],
    )
    report = (
        DataModel()
        .add_table("customers", customers, primary_key=["tenant", "id"])
        .add_table("orders", orders, primary_key="order")
        .add_relation(
            ("orders", ["tenant", "customer"]),
            ("customers", ["tenant", "id"]),
            name="customer_fk",
            nulls=nulls,
        )
        .validate()
    )
    relation = report.relations[0]
    assert not relation.valid
    assert relation.null_rows == 2
    assert relation.orphan_rows == 2
    assert relation.missing_keys == 1
    orphans = report.issues(relation="customer_fk", code="foreign_key_orphan")
    assert orphans["row_position"].tolist() == [3, 4]
    assert orphans["index"].tolist() == [7, 7]
    assert orphans["key"].tolist() == [("A", 9), ("A", 9)]
    null_issues = report.issues(relation="customer_fk", code="foreign_key_null")
    assert len(null_issues) == (2 if nulls == "forbid" else 0)


def test_null_reference_does_not_match_null_parent_under_match_simple():
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"key": [None]}))
        .add_table("children", pd.DataFrame({"key": [None]}))
        .add_relation("children.key", "parents.key")
        .validate()
    )
    assert report.valid
    assert report.relations[0].null_rows == 1
    assert report.relations[0].orphan_rows == 0


def test_referenced_nonnull_keys_must_be_unique_without_declared_primary_key():
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"key": [1, 1, None, None]}))
        .add_table("children", pd.DataFrame({"key": [1]}))
        .add_relation("children.key", "parents.key", name="fk")
        .validate()
    )
    relation = report.relations[0]
    assert not relation.valid
    assert relation.target_duplicate_keys == 1
    assert relation.orphan_rows == 0
    issues = report.issues(relation="fk", code="foreign_key_target_duplicate")
    assert issues["table"].tolist() == ["parents", "parents"]
    assert issues["row_position"].tolist() == [0, 1]


@pytest.mark.parametrize(
    "relationship,expected_valid", [("many_to_one", True), ("one_to_one", False)]
)
def test_foreign_key_cardinality_constrains_child_uniqueness(relationship, expected_valid):
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"key": [1]}), primary_key="key")
        .add_table(
            "children", pd.DataFrame({"row_id": [10, 11], "key": [1, 1]}), primary_key="row_id"
        )
        .add_relation("children.key", "parents.key", relationship=relationship)
        .validate()
    )
    assert report.valid is expected_valid
    assert report.relations[0].child_duplicate_keys == 1
    assert report.relations[0].observed_relationship == "many_to_one"


def test_large_adjacent_object_keys_and_nulls_preserve_orphan_identity():
    large = 2**53 + 1
    parents = pd.DataFrame({"key": pd.Series([large, large + 1, None], dtype=object)})
    children = pd.DataFrame({"key": [large + 1, large + 2, None]}, dtype=object, index=[0, 0, 0])
    report = (
        DataModel()
        .add_table("parents", parents)
        .add_table("children", children)
        .add_relation("children.key", "parents.key", name="fk")
        .validate()
    )
    relation = report.relations[0]
    assert relation.orphan_rows == relation.missing_keys == 1
    assert relation.target_duplicate_keys == 0
    assert relation.null_rows == 1
    orphan = report.issues(relation="fk", code="foreign_key_orphan").iloc[0]
    assert orphan["row_position"] == 1
    assert int(orphan["key"][0]) == large + 2


def test_table_registration_and_report_outputs_are_snapshots():
    parents = pd.DataFrame({"key": [1]})
    children = pd.DataFrame({"key": [1]})
    model = (
        DataModel().add_table("parents", parents, primary_key="key").add_table("children", children)
    )
    model.add_relation("children.key", "parents.key")
    children.loc[:, "key"] = 999
    parents.loc[:, "key"] = 888
    report = model.validate()
    assert report.valid
    output = report.issues()
    output.loc[0, "code"] = "injected"
    assert report.issues().empty
    assert model.validate().valid


def test_numeric_and_string_foreign_keys_are_not_silently_coerced():
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"key": [1]}))
        .add_table("children", pd.DataFrame({"key": ["1"]}))
        .add_relation("children.key", "parents.key")
        .validate()
    )
    assert not report.valid
    assert report.relations[0].orphan_rows == report.relations[0].missing_keys == 1


@pytest.mark.parametrize("kind", ["nullable", "categorical", "datetime"])
def test_standard_nullable_categorical_and_datetime_keys(kind):
    if kind == "nullable":
        parents = pd.DataFrame({"key": pd.Series([1], dtype="Int64")})
        children = pd.DataFrame({"key": pd.Series([1, pd.NA], dtype="Int64")})
    elif kind == "categorical":
        parents = pd.DataFrame({"key": pd.Categorical(["a"], categories=["a", "unused"])})
        children = pd.DataFrame({"key": pd.Categorical(["a", None], categories=["a", "other"])})
    else:
        parents = pd.DataFrame({"key": pd.to_datetime(["2024-01-01T00:00:00Z"])})
        children = pd.DataFrame({"key": pd.to_datetime(["2023-12-31T18:00:00-06:00", None])})
    report = (
        DataModel()
        .add_table("parents", parents, primary_key="key")
        .add_table("children", children)
        .add_relation("children.key", "parents.key")
        .validate()
    )
    assert report.valid
    assert report.relations[0].null_rows == 1
    assert report.relations[0].orphan_rows == 0


def test_empty_parent_and_child_tables_have_defined_integrity():
    empty = pd.DataFrame({"key": pd.Series([], dtype="Int64")})
    report = (
        DataModel()
        .add_table("parents", empty, primary_key="key")
        .add_table("children", empty, primary_key="key")
        .add_relation("children.key", "parents.key")
        .validate()
    )
    assert report.valid
    assert report.relations[0].orphan_rows == report.relations[0].missing_keys == 0
    orphans = (
        DataModel().add_table("parents", empty).add_table("children", pd.DataFrame({"key": [1, 1]}))
    )
    orphan_report = orphans.add_relation("children.key", "parents.key").validate()
    assert orphan_report.relations[0].orphan_rows == 2
    assert orphan_report.relations[0].missing_keys == 1


def test_validation_does_not_materialize_a_many_to_many_merge(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Relational membership validation must not materialize merge payloads")

    monkeypatch.setattr(pd.DataFrame, "merge", forbidden)
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"key": [1] * 1000}))
        .add_table("children", pd.DataFrame({"key": [1] * 1000}))
        .add_relation("children.key", "parents.key")
        .validate()
    )
    assert not report.valid
    assert report.relations[0].target_duplicate_keys == 1
    assert report.relations[0].orphan_rows == 0


def test_strict_json_serializes_dates_nulls_nonfinite_and_exact_integers():
    large = 2**53 + 1
    date = pd.Timestamp("2024-01-02T00:00:00Z")
    children = pd.DataFrame({"key": pd.Series([large, date, None, float("inf")], dtype=object)})
    parents = pd.DataFrame({"key": pd.Series([], dtype=object)})
    report = (
        DataModel()
        .add_table("parents", parents)
        .add_table("children", children)
        .add_relation("children.key", "parents.key", nulls="forbid")
        .validate()
    )
    payload = report.to_dict()
    encoded = json.dumps(payload, allow_nan=False)
    decoded = json.loads(report.to_json())
    assert decoded == payload
    assert str(large) in encoded
    assert date.isoformat() in encoded
    assert "null" in encoded
    assert "Infinity" not in encoded or '"Infinity"' in encoded
    assert "RELATIONAL" in report.explain().upper()
    keys = [issue["key"] for issue in payload["issues"]]
    assert [large] in keys
    assert [date.isoformat()] in keys
    assert [None] in keys
    assert isinstance(next(key[0] for key in keys if key == [large]), int)


@pytest.mark.parametrize(
    "value,expected",
    [
        (np.datetime64("2024-02-03T12:30:01.123456789", "ns"), "2024-02-03T12:30:01.123456789"),
        (np.timedelta64(123456789, "ns"), {"type": "timedelta64", "value": "P0DT0H0M0.123456789S"}),
    ],
)
def test_numpy_temporal_json_preserves_type_and_nanosecond_value(value, expected):
    source = pd.DataFrame({"key": pd.Series([value, value], dtype=object)})
    report = DataModel().add_table("items", source, primary_key="key").validate()
    serialized = report.to_dict()["issues"][0]["key"][0]
    assert serialized == expected


def test_invalid_schema_and_unsupported_relationship_are_rejected():
    model = DataModel().add_table("parents", pd.DataFrame({"key": [1]}))
    with pytest.raises(ModelError):
        model.add_table("parents", pd.DataFrame({"key": [2]}))
    with pytest.raises(ModelError):
        model.add_relation("unknown.key", "parents.key")
    with pytest.raises(ModelError):
        model.add_relation("parents.missing", "parents.key")
    with pytest.raises(ModelError):
        model.add_relation("parents.key", "parents.key", relationship="many_to_many")
