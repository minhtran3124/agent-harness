# Project

## Test execution

- **Test command:** `python3 -m pytest`
- **Targeted-run flags:** `python3 -m pytest tests/test_<module>.py -q`; `-x` stops at the first failure; `-k <name>` filters by name
- **Source → test mapping:** `<module>.py` → `tests/test_<module>.py`
- **Markers / coverage:** none
