# Project

## Test execution

- **Test command:** `python3 -m pytest`
- **Targeted-run flags:** `python3 -m pytest tests/test_<module>.py -q`; `-x` stops at the first failure; `-k <name>` filters by name
- **Source → test mapping:** `<module>.py` → `tests/test_<module>.py`; `inventory.py` is also used by `orders.py`, so a change to `inventory.py` must also run `tests/test_orders.py`
- **Markers / coverage:** none
