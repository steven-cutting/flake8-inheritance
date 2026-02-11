# Smoke Test Results

**Date:** 2026-02-11 (Initial documentation)

## Summary

**Overall Status:** ⚠️ TESTING INFRASTRUCTURE READY

This document will be populated with actual test results when the smoke tests are run against real-world codebases.

The smoke test infrastructure has been implemented and is ready to test against:
- CPython stdlib (Lib/ directory)
- requests library
- FastAPI framework

## How to Run

To execute smoke tests:

```bash
python3 scripts/smoke_test.py

# Or to specify a custom output file
python3 scripts/smoke_test.py --output custom_results.md

# To also generate JSON output
python3 scripts/smoke_test.py --json
```

## Expected Test Targets

### CPython stdlib
- **Repository:** https://github.com/python/cpython.git
- **Test Path:** Lib/
- **Purpose:** Validate against the Python standard library codebase

### requests
- **Repository:** https://github.com/psf/requests.git
- **Test Path:** src/requests/
- **Purpose:** Validate against a popular third-party HTTP library

### FastAPI
- **Repository:** https://github.com/tiangolo/fastapi.git
- **Test Path:** fastapi/
- **Purpose:** Validate against a modern async web framework

## Interpretation Guide

### Exit Codes
- **0** = No violations found (clean run)
- **1** = Violations found (expected behavior, plugin working correctly)
- **>1** = Error/crash (indicates a problem with the plugin)

### Success Criteria
A smoke test is considered successful if:
1. The plugin runs without crashing (exit code ≤ 1)
2. No unhandled exceptions occur
3. All files are analyzed without errors

### Violation Reporting
Violations (INH001, INH002) are expected and normal. The key metric is that the plugin completes analysis without errors, not that it finds zero violations.

## Notes

- Smoke tests use temporary directories for cloning (automatically cleaned up)
- Network failures are handled gracefully - tests continue for remaining projects
- Large codebases like CPython may take several minutes to analyze
- The script can be run multiple times safely (idempotent)

## Future Enhancements

- [ ] Add GitHub Actions workflow for periodic smoke testing
- [ ] Track violation trends over time
- [ ] Add more test projects (e.g., Django, Flask, pytest)
- [ ] Generate HTML reports with charts
- [ ] Add performance benchmarking
