"""Property-based tests for table sorting correctness.

Feature: bentwookie-web-ui-enhancements
Property 1: Table Sorting Correctness by Data Type

Validates: Requirements 1.1, 1.6

Note: Since the table sorter is JavaScript, these tests validate the sorting
logic by testing equivalent Python implementations that mirror the JS behavior.
"""

from hypothesis import given, settings, strategies as st


def compare_text(a: str, b: str) -> int:
    """Compare two text values (case-insensitive)."""
    if not a and not b:
        return 0
    if not a:
        return 1
    if not b:
        return -1
    a_lower = a.lower()
    b_lower = b.lower()
    if a_lower < b_lower:
        return -1
    elif a_lower > b_lower:
        return 1
    return 0


def compare_number(a: str, b: str) -> int:
    """Compare two numeric values."""
    if not a and not b:
        return 0
    if not a:
        return 1
    if not b:
        return -1
    try:
        num_a = float(a)
    except (ValueError, TypeError):
        num_a = 0
    try:
        num_b = float(b)
    except (ValueError, TypeError):
        num_b = 0
    if num_a < num_b:
        return -1
    elif num_a > num_b:
        return 1
    return 0


def compare_date(a: str, b: str) -> int:
    """Compare two date values."""
    from datetime import datetime

    if not a and not b:
        return 0
    if not a:
        return 1
    if not b:
        return -1

    try:
        date_a = datetime.fromisoformat(a.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return 1  # Invalid dates go to end

    try:
        date_b = datetime.fromisoformat(b.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return -1  # Invalid dates go to end

    if date_a < date_b:
        return -1
    elif date_a > date_b:
        return 1
    return 0


def sort_rows(rows: list[str], sort_type: str, direction: str = "asc") -> list[str]:
    """Sort rows using the appropriate comparison function."""
    if sort_type == "number":
        compare_fn = compare_number
    elif sort_type == "date":
        compare_fn = compare_date
    else:
        compare_fn = compare_text

    from functools import cmp_to_key

    sorted_rows = sorted(rows, key=cmp_to_key(compare_fn))
    if direction == "desc":
        sorted_rows = list(reversed(sorted_rows))
    return sorted_rows


class TestPropertyTableSortingText:
    """Property 1: Table Sorting Correctness - Text Type.

    For any array of text values, sorting SHALL produce rows ordered
    alphabetically (case-insensitive).

    **Validates: Requirements 1.1, 1.6**
    """

    @settings(max_examples=25)
    @given(st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=20))
    def test_text_sorting_produces_ordered_result(self, values: list[str]):
        """Sorting text values produces alphabetically ordered result."""
        sorted_asc = sort_rows(values, "text", "asc")

        # Verify ordering: each element should be <= next element
        for i in range(len(sorted_asc) - 1):
            cmp = compare_text(sorted_asc[i], sorted_asc[i + 1])
            assert cmp <= 0, f"Not sorted: {sorted_asc[i]!r} > {sorted_asc[i + 1]!r}"

    @settings(max_examples=25)
    @given(st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=20))
    def test_text_sorting_desc_reverses_order(self, values: list[str]):
        """Descending sort reverses the ascending order."""
        sorted_asc = sort_rows(values, "text", "asc")
        sorted_desc = sort_rows(values, "text", "desc")

        # Verify desc is reverse of asc
        assert sorted_desc == list(reversed(sorted_asc))

    @settings(max_examples=25)
    @given(st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=20))
    def test_text_sorting_preserves_elements(self, values: list[str]):
        """Sorting preserves all original elements."""
        sorted_values = sort_rows(values, "text", "asc")
        assert sorted(values) == sorted(sorted_values)


class TestPropertyTableSortingNumber:
    """Property 1: Table Sorting Correctness - Number Type.

    For any array of numeric values, sorting SHALL produce rows ordered
    numerically.

    **Validates: Requirements 1.1, 1.6**
    """

    @settings(max_examples=25)
    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=0, max_size=20))
    def test_number_sorting_produces_ordered_result(self, values: list[float]):
        """Sorting numeric values produces numerically ordered result."""
        str_values = [str(v) for v in values]
        sorted_asc = sort_rows(str_values, "number", "asc")

        # Verify ordering: each element should be <= next element
        for i in range(len(sorted_asc) - 1):
            cmp = compare_number(sorted_asc[i], sorted_asc[i + 1])
            assert cmp <= 0, f"Not sorted: {sorted_asc[i]} > {sorted_asc[i + 1]}"

    @settings(max_examples=25)
    @given(st.lists(st.integers(min_value=-10000, max_value=10000), min_size=0, max_size=20))
    def test_integer_sorting_produces_ordered_result(self, values: list[int]):
        """Sorting integer values produces numerically ordered result."""
        str_values = [str(v) for v in values]
        sorted_asc = sort_rows(str_values, "number", "asc")

        # Convert back to numbers and verify ordering
        nums = [float(v) for v in sorted_asc]
        for i in range(len(nums) - 1):
            assert nums[i] <= nums[i + 1], f"Not sorted: {nums[i]} > {nums[i + 1]}"

    @settings(max_examples=25)
    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=0, max_size=20))
    def test_number_sorting_preserves_elements(self, values: list[float]):
        """Sorting preserves all original elements."""
        str_values = [str(v) for v in values]
        sorted_values = sort_rows(str_values, "number", "asc")
        assert sorted(str_values) == sorted(sorted_values)


class TestPropertyTableSortingDate:
    """Property 1: Table Sorting Correctness - Date Type.

    For any array of date values, sorting SHALL produce rows ordered
    chronologically.

    **Validates: Requirements 1.1, 1.6**
    """

    @settings(max_examples=25)
    @given(st.lists(st.datetimes(), min_size=0, max_size=20))
    def test_date_sorting_produces_ordered_result(self, values):
        """Sorting date values produces chronologically ordered result."""
        str_values = [v.isoformat() for v in values]
        sorted_asc = sort_rows(str_values, "date", "asc")

        # Verify ordering: each element should be <= next element
        for i in range(len(sorted_asc) - 1):
            cmp = compare_date(sorted_asc[i], sorted_asc[i + 1])
            assert cmp <= 0, f"Not sorted: {sorted_asc[i]} > {sorted_asc[i + 1]}"

    @settings(max_examples=25)
    @given(st.lists(st.datetimes(), min_size=0, max_size=20))
    def test_date_sorting_preserves_elements(self, values):
        """Sorting preserves all original elements."""
        str_values = [v.isoformat() for v in values]
        sorted_values = sort_rows(str_values, "date", "asc")
        assert sorted(str_values) == sorted(sorted_values)


class TestPropertyTableSortingEmptyValues:
    """Property 1: Table Sorting Correctness - Empty Value Handling.

    Empty/null values SHALL be pushed to the end of sorted results.

    **Validates: Requirements 1.1, 1.6**
    """

    @settings(max_examples=25)
    @given(
        st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10),
        st.integers(min_value=1, max_value=5),
    )
    def test_empty_values_pushed_to_end_text(self, non_empty: list[str], num_empty: int):
        """Empty text values are pushed to the end when sorting."""
        values = non_empty + [""] * num_empty
        sorted_values = sort_rows(values, "text", "asc")

        # All empty values should be at the end
        empty_count = sum(1 for v in sorted_values if not v)
        assert empty_count == num_empty

        # Find first empty value position
        first_empty_idx = next((i for i, v in enumerate(sorted_values) if not v), len(sorted_values))

        # All values after first empty should also be empty
        for i in range(first_empty_idx, len(sorted_values)):
            assert not sorted_values[i], f"Non-empty value after empty: {sorted_values[i]!r}"

    @settings(max_examples=25)
    @given(
        st.lists(st.integers(min_value=1, max_value=1000), min_size=1, max_size=10),
        st.integers(min_value=1, max_value=5),
    )
    def test_empty_values_pushed_to_end_number(self, non_empty: list[int], num_empty: int):
        """Empty numeric values are pushed to the end when sorting."""
        values = [str(v) for v in non_empty] + [""] * num_empty
        sorted_values = sort_rows(values, "number", "asc")

        # All empty values should be at the end
        empty_count = sum(1 for v in sorted_values if not v)
        assert empty_count == num_empty
