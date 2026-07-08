# Changelog

## [1.2.0] - 2026-07-08

### Added
- Multi-provider support: Groq (free tier), Google Gemini (free tier), and
  Ollama (fully local, free) alongside OpenAI, all via the same
  OpenAI-compatible chat completions API -- just a provider config + base_url
  swap. New "Model provider" dropdown and per-provider "Model" override field
  in the sidebar.
- Defensive markdown-code-fence stripping in `run_gap_analysis`, since some
  OpenAI-compatible providers wrap JSON responses in ``` fences even when
  asked not to.
- Provider-aware error messages, including a specific message for Ollama
  connection failures (server not running / model not pulled).
- 8 new tests covering the PROVIDERS config and per-provider UI behavior.

## [1.1.0] - 2026-07-08

### Added
- PCI DSS v4.0.1 as a 5th supported framework (12 principal requirements)
- Compare two versions mode: run the same framework assessment against a v1/v2
  document pair and get a per-domain Improved/Regressed/Unchanged diff
- Test suite (`tests/test_app.py`, 19 tests) covering framework data, scoring/diff
  logic, and full UI flows via `streamlit.testing.v1.AppTest` with OpenAI mocked

### Fixed
- "Load sample document" buttons now correctly populate the text area (previous
  implementation set session state after the widget was already instantiated,
  which silently failed to persist across the rerun)
- Replaced deprecated `use_container_width` dataframe parameter with `width`

### Changed
- UI code now guarded by `if __name__ == "__main__":` so `app.py` can be
  imported for testing without executing any Streamlit calls

## [1.0.0] - 2026-06-30

### Added
- Initial release
- PDF document upload support (pypdf)
- Four frameworks: ISO 27001:2022, NIST CSF 2.0, NIS2, DORA
- Filterable gap table with High/Medium/Low risk ratings
- Compliance score and per-domain coverage breakdown
- CSV export and built-in sample document
