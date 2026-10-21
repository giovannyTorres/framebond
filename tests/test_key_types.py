"""Type-aware identifiers and actionable foreign-key diagnostics."""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pandas.testing import assert_frame_equal

from framebond import DataModel, KeyIndex, PandasBackend


@pytest.mark.parametrize("boolean,number", [(True, 1), (False, 0), (np.bool_(True), 1.0)])
@pytest.mark.parametrize("reverse", [False, True])
def test_booleans_never_reference_numeric_identifiers(boolean, number, reverse):
    child, parent = (number, boolean) if reverse else (boolean, number)
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"id": [parent]}, dtype=object))
        .add_table("children", pd.DataFrame({"id": [child]}, dtype=object))
        .add_relation("children.id", "parents.id")
        .validate()
    )
    assert not report.valid
    assert report.relations[0].orphan_rows == 1
    assert len(report.relations[0].type_mismatches) == 1
    assert report.issues(code="foreign_key_orphan")["key"].tolist() == [(child,)]


def test_boolean_and_number_keys_remain_distinct_in_mixed_composite_identifiers():
    parents = pd.DataFrame({"tenant": ["a"] * 4, "id": [1, True, 0, False]}, dtype=object)
    children = pd.DataFrame(
        {"tenant": ["a"] * 6, "id": [True, 1.0, False, 0, 2, "1"]}, dtype=object
    )
    original = parents.copy(deep=True)
    report = (
        DataModel()
        .add_table("parents", parents, primary_key=["tenant", "id"])
        .add_table("children", children)
        .add_relation(("children", ["tenant", "id"]), ("parents", ["tenant", "id"]))
        .validate()
    )
    assert report.tables[0].primary_key_valid
    assert report.relations[0].target_duplicate_keys == 0
    assert report.relations[0].orphan_rows == 2
    assert report.issues(code="foreign_key_orphan")["row_position"].tolist() == [4, 5]
    assert report.issues(code="foreign_key_type_mismatch")["row_position"].tolist() == [5]
    index = PandasBackend().index(parents, ("tenant", "id"))
    assert index.positions_for(("a", True)) == (1,)
    assert index.positions_for(("a", 1)) == (0,)
    assert index.positions_for(("a", False)) == (3,)
    assert index.positions_for(("a", 0.0)) == (2,)
    assert index.positions_for(("a", None)) == ()
    assert_frame_equal(parents, original)


def test_boolean_duplicates_are_counted_without_collapsing_numeric_keys():
    frame = pd.DataFrame({"id": [True, 1, np.bool_(True), 1.0, False, 0]}, dtype=object)
    report = DataModel().add_table("items", frame, primary_key="id").validate()
    assert report.tables[0].duplicate_keys == 2
    assert report.tables[0].duplicate_rows == 4
    assert report.issues(code="primary_key_duplicate")["row_position"].tolist() == [0, 1, 2, 3]


def test_custom_backend_uses_type_aware_matching_at_the_model_boundary():
    class OriginalTupleBackend:
        def index(self, frame, columns):
            keys = tuple(frame[list(columns)].itertuples(index=False, name=None))
            positions = {}
            nulls = []
            for pos, key in enumerate(keys):
                if any(value is None for value in key):
                    nulls.append(pos)
                else:
                    positions.setdefault(key, []).append(pos)
            return KeyIndex(
                keys, tuple(nulls), {key: tuple(rows) for key, rows in positions.items()}
            )

    model = DataModel()
    model._backend = OriginalTupleBackend()
    report = (
        model.add_table(
            "parents", pd.DataFrame({"id": [1, True, None]}, dtype=object), primary_key="id"
        )
        .add_table("children", pd.DataFrame({"id": [True, 1, False]}, dtype=object))
        .add_relation("children.id", "parents.id")
        .validate()
    )
    assert report.tables[0].duplicate_keys == 0
    assert report.relations[0].target_duplicate_keys == 0
    assert report.relations[0].orphan_rows == 1
    assert report.issues(code="foreign_key_orphan")["key"].tolist() == [(False,)]


def test_manually_constructed_index_looks_up_original_boolean_and_numeric_rows():
    index = KeyIndex(((True,), (1,), (False,), (0,)), (), {(True,): (0, 1), (False,): (2, 3)})
    assert index.positions_for((True,)) == (0,)
    assert index.positions_for((1,)) == (1,)
    assert index.positions_for((False,)) == (2,)
    assert index.positions_for((0,)) == (3,)


def test_custom_backend_nonboolean_matching_components_are_preserved():
    class CasefoldBackend:
        def index(self, frame, columns):
            keys = tuple(frame[list(columns)].itertuples(index=False, name=None))
            positions = {}
            for pos, key in enumerate(keys):
                normalized = tuple(
                    value.casefold() if isinstance(value, str) else value for value in key
                )
                positions.setdefault(normalized, []).append(pos)
            return KeyIndex(keys, (), {key: tuple(rows) for key, rows in positions.items()})

    model = DataModel()
    model._backend = CasefoldBackend()
    report = (
        model.add_table("parents", pd.DataFrame({"tenant": ["ALICE"], "id": [1]}))
        .add_table(
            "children", pd.DataFrame({"tenant": ["alice", "Alice"], "id": [1, True]}, dtype=object)
        )
        .add_relation(("children", ["tenant", "id"]), ("parents", ["tenant", "id"]))
        .validate()
    )
    assert report.relations[0].orphan_rows == 1
    assert report.issues(code="foreign_key_orphan")["row_position"].tolist() == [1]
    assert report.issues(code="foreign_key_orphan")["key"].tolist() == [("Alice", True)]


@pytest.mark.parametrize(
    "child,parent,child_type,parent_type",
    [
        ("1", 1, "string", "number"),
        (1, "1", "number", "string"),
        (
            pd.Timestamp("2024-01-01", tz="UTC"),
            pd.Timestamp("2024-01-01"),
            "datetime-aware",
            "datetime-naive",
        ),
        (
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-01", tz="UTC"),
            "datetime-naive",
            "datetime-aware",
        ),
        (np.datetime64("2024-01-01"), "2024-01-01", "datetime-naive", "string"),
        (np.timedelta64(1, "D"), "1 day", "timedelta", "string"),
        (timedelta(days=1), "1 day", "timedelta", "string"),
        (date(2024, 1, 1), "2024-01-01", "datetime.date", "string"),
        (Decimal("1"), "1", "number", "string"),
    ],
)
def test_incompatible_orphans_explain_types_and_preserve_original_issues(
    child, parent, child_type, parent_type
):
    children = pd.DataFrame({"id": [child, None, child]}, dtype=object, index=[7, 7, 9])
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"id": [parent]}, dtype=object))
        .add_table("children", children)
        .add_relation("children.id", "parents.id", name="fk")
        .validate()
    )
    result = report.relations[0]
    assert result.orphan_rows == 2
    assert result.missing_keys == 1
    assert result.null_rows == 1
    message = result.type_mismatches[0]
    assert f"children.id has {child_type} keys" in message
    assert f"parents.id types ({parent_type})" in message
    assert "align key types explicitly" in report.explain()
    issues = report.issues(relation="fk", code="foreign_key_type_mismatch")
    assert issues["row_position"].tolist() == [0, 2]
    assert issues["index"].tolist() == [7, 9]
    assert all(type(key[0]) is type(child) for key in issues["key"])
    assert report.to_dict()["relations"][0]["type_mismatches"] == [message]


def test_compatible_types_with_missing_values_are_plain_orphans():
    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"id": [1]}, dtype=object))
        .add_table("children", pd.DataFrame({"id": [2.0, Decimal("1")]}, dtype=object))
        .add_relation("children.id", "parents.id")
        .validate()
    )
    assert report.relations[0].orphan_rows == 1
    assert not report.relations[0].type_mismatches
    assert report.issues(code="foreign_key_type_mismatch").empty


scalar_values = st.lists(
    st.one_of(st.none(), st.booleans(), st.integers(-2, 2), st.text(alphabet="12", max_size=2)),
    max_size=25,
)


@given(scalar_values, scalar_values)
@settings(max_examples=100, derandomize=True, deadline=None)
def test_mixed_type_membership_against_independent_pairwise_comparison(child, parent):
    def equal(left, right):
        if isinstance(left, bool) != isinstance(right, bool):
            return False
        return left == right

    report = (
        DataModel()
        .add_table("parents", pd.DataFrame({"id": parent}, dtype=object))
        .add_table("children", pd.DataFrame({"id": child}, dtype=object))
        .add_relation("children.id", "parents.id")
        .validate()
    )
    expected = [
        row
        for row, value in enumerate(child)
        if value is not None
        and not any(other is not None and equal(value, other) for other in parent)
    ]
    assert report.relations[0].orphan_rows == len(expected)
    assert report.issues(code="foreign_key_orphan")["row_position"].tolist() == expected
