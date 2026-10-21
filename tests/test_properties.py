from collections import Counter

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from framebond import DataModel

values = st.lists(st.one_of(st.none(), st.integers(-10, 10)), max_size=60)


@given(values, values)
@settings(max_examples=100, derandomize=True, deadline=None)
def test_integrity_against_independent_counter_and_membership(child_values, parent_values):
    child = pd.DataFrame({"id": pd.Series(child_values, dtype=object)})
    parent = pd.DataFrame({"id": pd.Series(parent_values, dtype=object)})
    model = DataModel().add_table("c", child).add_table("p", parent, primary_key="id")
    model.add_relation("c.id", "p.id")
    report = model.validate()
    parent_counts = Counter(value for value in parent_values if value is not None)
    child_counts = Counter(value for value in child_values if value is not None)
    orphan_keys = {value for value in child_counts if value not in parent_counts}
    assert report.relations[0].orphan_rows == sum(child_counts[key] for key in orphan_keys)
    assert report.relations[0].missing_keys == len(orphan_keys)
    assert report.relations[0].null_rows == sum(value is None for value in child_values)
    assert report.tables[1].duplicate_keys == sum(count > 1 for count in parent_counts.values())
    assert report.tables[1].duplicate_rows == sum(
        count for count in parent_counts.values() if count > 1
    )
    assert report.tables[1].primary_key_valid == (
        None not in parent_values and all(count == 1 for count in parent_counts.values())
    )


@given(
    st.lists(
        st.tuples(st.one_of(st.none(), st.integers(0, 5)), st.one_of(st.none(), st.integers(0, 5))),
        max_size=50,
    )
)
@settings(max_examples=70, derandomize=True, deadline=None)
def test_composite_match_simple_null_policy(rows):
    child = pd.DataFrame(rows, columns=["a", "b"], dtype=object)
    parent = pd.DataFrame(
        [(i, j) for i in range(3) for j in range(3)], columns=["a", "b"], dtype=object
    )
    model = DataModel().add_table("c", child).add_table("p", parent, primary_key=["a", "b"])
    model.add_relation(("c", ["a", "b"]), ("p", ["a", "b"]))
    report = model.validate()
    expected = [
        row
        for row in rows
        if None not in row and row not in {(i, j) for i in range(3) for j in range(3)}
    ]
    assert report.relations[0].orphan_rows == len(expected)
    assert report.relations[0].missing_keys == len(set(expected))
