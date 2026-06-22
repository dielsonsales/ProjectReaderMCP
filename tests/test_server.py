import pytest
from server import format_timestamp, list_files, read_file, recursive_search

def test_format_timestamp_valid():
    from server import format_timestamp
    timestamp = 1700000000.0
    expected_output = "2023-11-14 22:13:20"
    assert format_timestamp(timestamp) == expected_output, "The format_timestamp function did not return the expected output."
