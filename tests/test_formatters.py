import pytest
from dev_local_artifact_pruner.utils import format_bytes, format_relative_time


def test_format_bytes_zero():
    assert format_bytes(0) == "0 B"


def test_format_bytes_single_byte():
    assert format_bytes(1) == "1 B"


def test_format_bytes_under_one_kilobyte():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1023) == "1023 B"


def test_format_bytes_exact_kilobyte():
    assert format_bytes(1024) == "1.00 KB"


def test_format_bytes_fractional_kilobyte():
    assert format_bytes(1536) == "1.50 KB"


def test_format_bytes_under_one_megabyte():
    assert format_bytes(1048575) == "1024.00 KB"


def test_format_bytes_exact_megabyte():
    assert format_bytes(1048576) == "1.00 MB"


def test_format_bytes_fractional_megabyte():
    assert format_bytes(2500000) == "2.38 MB"


def test_format_bytes_exact_gigabyte():
    assert format_bytes(1073741824) == "1.00 GB"


def test_format_bytes_fractional_gigabyte():
    four_and_half_gb = int(4.5 * 1024 * 1024 * 1024)
    assert format_bytes(four_and_half_gb) == "4.50 GB"


def test_format_bytes_terabytes_and_petabytes():
    one_tb = 1024 * 1024 * 1024 * 1024
    one_pb = one_tb * 1024
    assert format_bytes(one_tb) == "1.00 TB"
    assert format_bytes(one_pb) == "1.00 PB"


def test_format_bytes_negative_raises_value_error():
    with pytest.raises(ValueError, match="Size in bytes cannot be negative"):
        format_bytes(-1)


def test_format_relative_time_none():
    assert format_relative_time(None) == "desconhecido"


def test_format_relative_time_zero_or_negative():
    assert format_relative_time(0) == "hoje"
    assert format_relative_time(-1) == "hoje"
    assert format_relative_time(-10) == "hoje"


def test_format_relative_time_one_day():
    assert format_relative_time(1) == "há 1 dia"


def test_format_relative_time_multiple_days():
    assert format_relative_time(2) == "há 2 dias"
    assert format_relative_time(15) == "há 15 dias"
    assert format_relative_time(29) == "há 29 dias"


def test_format_relative_time_one_month():
    assert format_relative_time(30) == "há 1 mês"
    assert format_relative_time(45) == "há 1 mês"
    assert format_relative_time(59) == "há 1 mês"


def test_format_relative_time_multiple_months():
    assert format_relative_time(60) == "há 2 meses"
    assert format_relative_time(90) == "há 3 meses"
    assert format_relative_time(240) == "há 8 meses"
    assert format_relative_time(330) == "há 11 meses"
    assert format_relative_time(364) == "há 12 meses"


def test_format_relative_time_one_year():
    assert format_relative_time(365) == "há 1 ano"
    assert format_relative_time(400) == "há 1 ano"
    assert format_relative_time(729) == "há 1 ano"


def test_format_relative_time_multiple_years():
    assert format_relative_time(730) == "há 2 anos"
    assert format_relative_time(1095) == "há 3 anos"
