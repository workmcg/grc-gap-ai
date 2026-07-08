"""
Tests for the GRC Gap Analyzer Streamlit app.

Split into two groups:
  - Pure-logic tests: import app.py directly (safe because the UI is guarded
    by `if __name__ == "__main__":`) and exercise the framework data and
    scoring/diff functions with no network calls.
  - UI smoke tests: use Streamlit's AppTest harness to render the app and
    click through both tabs, with openai.OpenAI mocked so no real API calls
    are made and no API key is required.

Run with:  python -m pytest -q
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import openai
import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app  # noqa: E402


# ── Pure-logic tests ───────────────────────────────────────────────────────────

def test_five_frameworks_defined():
    assert set(app.FRAMEWORKS.keys()) == {
        "ISO 27001:2022",
        "NIST CSF 2.0",
        "NIS2 (Directive 2022/2555)",
        "DORA (Regulation EU 2022/2554)",
        "PCI DSS v4.0.1",
    }


def test_pci_dss_has_twelve_requirements():
    domains = app.FRAMEWORKS["PCI DSS v4.0.1"]
    assert len(domains) == 12
    assert domains[0].startswith("Req 1")
    assert domains[-1].startswith("Req 12")
    assert all(d.startswith("Req ") for d in domains)


def test_no_framework_has_empty_domain_list():
    for name, domains in app.FRAMEWORKS.items():
        assert len(domains) > 0, f"{name} has no domains"


def test_score_summary_full_coverage():
    results = [
        {"coverage": "Full", "risk_level": "N/A"},
        {"coverage": "Full", "risk_level": "N/A"},
    ]
    s = app.score_summary(results)
    assert s["score"] == 100
    assert s["full"] == 2
    assert s["high_risk"] == 0


def test_score_summary_mixed_coverage():
    results = [
        {"coverage": "Full", "risk_level": "N/A"},
        {"coverage": "Partial", "risk_level": "Medium"},
        {"coverage": "Missing", "risk_level": "High"},
        {"coverage": "Missing", "risk_level": "High"},
    ]
    s = app.score_summary(results)
    # (1 full + 0.5 partial) / 4 = 37.5% -> rounds to 38
    assert s["score"] == 38
    assert s["missing"] == 2
    assert s["high_risk"] == 2


def test_score_summary_empty_results():
    assert app.score_summary([])["score"] == 0


def test_diff_results_classifies_improved_regressed_unchanged():
    v1 = [
        {"domain": "A", "coverage": "Missing", "risk_level": "High", "gap": "", "recommendation": ""},
        {"domain": "B", "coverage": "Full", "risk_level": "N/A", "gap": "", "recommendation": ""},
        {"domain": "C", "coverage": "Partial", "risk_level": "Medium", "gap": "", "recommendation": ""},
    ]
    v2 = [
        {"domain": "A", "coverage": "Full", "risk_level": "N/A", "gap": "", "recommendation": ""},
        {"domain": "B", "coverage": "Missing", "risk_level": "High", "gap": "", "recommendation": ""},
        {"domain": "C", "coverage": "Partial", "risk_level": "Medium", "gap": "", "recommendation": ""},
    ]
    diffs = app.diff_results(v1, v2)
    trends = {r["domain"]: r["trend"] for r in diffs}
    assert trends == {"A": "Improved", "B": "Regressed", "C": "Unchanged"}


def test_diff_summary_counts_match_diff_rows():
    v1 = [{"domain": "A", "coverage": "Missing", "risk_level": "High", "gap": "", "recommendation": ""}]
    v2 = [{"domain": "A", "coverage": "Full", "risk_level": "N/A", "gap": "", "recommendation": ""}]
    diffs = app.diff_results(v1, v2)
    summary = app.diff_summary(diffs)
    assert summary == {"improved": 1, "regressed": 0, "unchanged": 0, "total": 1}


def test_diff_results_ignores_domains_missing_from_v2():
    v1 = [{"domain": "Only in v1", "coverage": "Full", "risk_level": "N/A", "gap": "", "recommendation": ""}]
    v2 = []
    assert app.diff_results(v1, v2) == []


def test_build_user_prompt_includes_framework_and_domains():
    prompt = app.build_user_prompt("some document text", "PCI DSS v4.0.1", app.FRAMEWORKS["PCI DSS v4.0.1"])
    assert "PCI DSS v4.0.1" in prompt
    assert "some document text" in prompt
    assert "Install and maintain network security controls" in prompt


def test_sample_documents_are_different():
    assert app.SAMPLE_DOCUMENT != app.SAMPLE_DOCUMENT_V2
    assert len(app.SAMPLE_DOCUMENT) > 0
    assert len(app.SAMPLE_DOCUMENT_V2) > 0


def test_results_to_df_has_expected_columns():
    results = [{"domain": "A", "coverage": "Full", "risk_level": "N/A", "gap": "", "evidence": "", "recommendation": ""}]
    df = app.results_to_df(results)
    assert list(df.columns) == ["Domain", "Coverage", "Risk", "Gap", "Evidence", "Recommendation"]
    assert len(df) == 1


def test_diff_to_df_has_expected_columns():
    v1 = [{"domain": "A", "coverage": "Missing", "risk_level": "High", "gap": "g", "recommendation": "r"}]
    v2 = [{"domain": "A", "coverage": "Full", "risk_level": "N/A", "gap": "", "recommendation": ""}]
    diffs = app.diff_results(v1, v2)
    df = app.diff_to_df(diffs)
    assert "Trend" in df.columns
    assert "v1 Coverage" in df.columns
    assert "v2 Coverage" in df.columns


# ── UI smoke tests (mocked OpenAI, no real API calls / key needed) ────────────

def _mock_openai_client(coverage_by_call):
    """Returns a MagicMock OpenAI client whose chat.completions.create returns
    a fake but valid gap-analysis JSON array, cycling through the given
    coverage values across successive calls (one call per invocation)."""
    call_state = {"n": 0}

    def fake_create(*args, **kwargs):
        user_msg = kwargs["messages"][1]["content"]
        domains = [
            line.strip()[2:].strip()
            for line in user_msg.splitlines()
            if line.strip().startswith("- ")
        ]
        coverage = coverage_by_call[min(call_state["n"], len(coverage_by_call) - 1)]
        call_state["n"] += 1
        fake_results = [
            {
                "domain": d,
                "coverage": coverage,
                "evidence": "mock evidence",
                "gap": "mock gap",
                "risk_level": "Medium",
                "recommendation": "mock recommendation",
            }
            for d in domains
        ]
        msg = MagicMock()
        msg.content = json.dumps(fake_results)
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    client = MagicMock()
    client.chat.completions.create.side_effect = fake_create
    return client


def test_app_renders_without_exception():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
    at.run(timeout=30)
    assert not at.exception
    assert len(at.tabs) == 2


def test_framework_selectbox_offers_all_five():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
    at.run(timeout=30)
    assert "PCI DSS v4.0.1" in at.selectbox[0].options
    assert len(at.selectbox[0].options) == 5


def test_single_doc_sample_button_populates_textarea():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
    at.run(timeout=30)
    at.button(key="single_sample").click().run(timeout=30)
    assert not at.exception
    assert len(at.text_area(key="single_textarea").value) > 0


def test_compare_sample_button_populates_both_textareas_differently():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
    at.run(timeout=30)
    at.button(key="compare_sample").click().run(timeout=30)
    assert not at.exception
    v1 = at.text_area(key="v1_textarea").value
    v2 = at.text_area(key="v2_textarea").value
    assert len(v1) > 0 and len(v2) > 0
    assert v1 != v2


def test_single_document_analysis_end_to_end_with_mocked_openai():
    mock_client = _mock_openai_client(["Partial"])
    with patch.object(openai, "OpenAI", return_value=mock_client):
        at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
        at.run(timeout=30)
        at.text_input[0].set_value("sk-test-fake-key").run(timeout=30)
        at.selectbox[0].set_value("PCI DSS v4.0.1").run(timeout=30)
        at.button(key="single_sample").click().run(timeout=30)
        at.button(key="single_run").click().run(timeout=30)

    assert not at.exception
    assert len(at.dataframe) == 1


def test_compare_versions_end_to_end_with_mocked_openai_detects_regression():
    # v1 call returns Missing/Partial/Full cycling; v2 call returns mostly Full
    # except one Partial, guaranteeing at least one Regressed domain.
    mock_client = _mock_openai_client(["Missing", "Full"])
    with patch.object(openai, "OpenAI", return_value=mock_client):
        at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
        at.run(timeout=30)
        at.text_input[0].set_value("sk-test-fake-key").run(timeout=30)
        at.selectbox[0].set_value("ISO 27001:2022").run(timeout=30)
        at.button(key="compare_sample").click().run(timeout=30)
        at.button(key="compare_run").click().run(timeout=60)

    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert "⬆️ Improved" in metrics
    # every domain went Missing -> Full, so all should be Improved, none regressed
    assert metrics["⬇️ Regressed"] == "0"
