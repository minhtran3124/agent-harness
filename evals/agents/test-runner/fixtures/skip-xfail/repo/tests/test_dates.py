import sys

import pytest

from dates import is_leap


def test_leap_2024():
    assert is_leap(2024)


def test_not_leap_1900():
    assert not is_leap(1900)


def test_leap_2000():
    assert is_leap(2000)


def test_not_leap_2023():
    assert not is_leap(2023)


@pytest.mark.skipif(sys.version_info >= (3,), reason="python 2 calendar compatibility check")
def test_python2_calendar():
    assert is_leap(1996)


@pytest.mark.xfail(reason="known: proleptic Gregorian years before 1582 are not handled", strict=True)
def test_julian_year_1500():
    assert is_leap(1500)
