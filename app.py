"""
GRC Gap Analyzer
================
AI-powered compliance gap analysis tool.
Paste or upload a policy document, select a framework,
and get a structured gap report with risk ratings and remediation guidance.
Also supports comparing two versions of a document to track compliance drift.

Frameworks supported: ISO 27001:2022 · NIST CSF 2.0 · NIS2 · DORA · PCI DSS v4.0.1
AI backend: OpenAI GPT-4o
"""

import os
import io
import json
import textwrap

import streamlit as st
import openai
import pandas as pd

try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GRC Gap Analyzer",
    page_icon="🔒",
    layout="wide",
)

# ── Framework definitions ─────────────────────────────────────────────────────

FRAMEWORKS = {
    "ISO 27001:2022": [
        "5 – Organizational controls",
        "6 – People controls",
        "7 – Physical controls",
        "8.1 – User endpoint devices",
        "8.2 – Privileged access rights",
        "8.3 – Information access restriction",
        "8.4 – Access to source code",
        "8.5 – Secure authentication",
        "8.6 – Capacity management",
        "8.7 – Protection against malware",
        "8.8 – Management of technical vulnerabilities",
        "8.9 – Configuration management",
        "8.10 – Information deletion",
        "8.11 – Data masking",
        "8.12 – Data leakage prevention",
        "8.13 – Information backup",
        "8.14 – Redundancy of information processing facilities",
        "8.15 – Logging",
        "8.16 – Monitoring activities",
        "8.17 – Clock synchronisation",
        "8.18 – Use of privileged utility programs",
        "8.19 – Installation of software on operational systems",
        "8.20 – Networks security",
        "8.21 – Security of network services",
        "8.22 – Segregation of networks",
        "8.23 – Web filtering",
        "8.24 – Use of cryptography",
        "8.25 – Secure development life cycle",
        "8.26 – Application security requirements",
        "8.27 – Secure system architecture and engineering principles",
        "8.28 – Secure coding",
        "8.29 – Security testing in development and acceptance",
        "8.30 – Outsourced development",
        "8.31 – Separation of development, test and production",
        "8.32 – Change management",
        "8.33 – Test information",
        "8.34 – Protection of information systems during audit testing",
    ],
    "NIST CSF 2.0": [
        "GV.OC – Organizational Context",
        "GV.RM – Risk Management Strategy",
        "GV.RR – Roles, Responsibilities, and Authorities",
        "GV.PO – Policy",
        "GV.OV – Oversight",
        "GV.SC – Cybersecurity Supply Chain Risk Management",
        "ID.AM – Asset Management",
        "ID.RA – Risk Assessment",
        "ID.IM – Improvement",
        "PR.AA – Identity Management, Authentication, and Access Control",
        "PR.AT – Awareness and Training",
        "PR.DS – Data Security",
        "PR.PS – Platform Security",
        "PR.IR – Technology Infrastructure Resilience",
        "DE.CM – Continuous Monitoring",
        "DE.AE – Adverse Event Analysis",
        "RS.MA – Incident Management",
        "RS.AN – Incident Analysis",
        "RS.CO – Incident Response Reporting and Communication",
        "RS.MI – Incident Mitigation",
        "RC.RP – Incident Recovery Plan Execution",
        "RC.CO – Incident Recovery Communication",
    ],
    "NIS2 (Directive 2022/2555)": [
        "Art 21.2a – Policies on risk analysis and information system security",
        "Art 21.2b – Incident handling",
        "Art 21.2c – Business continuity & crisis management",
        "Art 21.2d – Supply chain security",
        "Art 21.2e – Security in network and information systems acquisition",
        "Art 21.2f – Policies and procedures to assess cybersecurity measures",
        "Art 21.2g – Basic cyber hygiene practices and cybersecurity training",
        "Art 21.2h – Policies and procedures on use of cryptography",
        "Art 21.2i – Human resources security, access control and asset management",
        "Art 21.2j – Use of multi-factor authentication",
        "Art 23 – Incident reporting obligations",
        "Art 24 – Use of certified ICT products and services",
    ],
    "DORA (Regulation EU 2022/2554)": [
        "Art 5 – ICT risk management framework",
        "Art 6 – ICT risk management systems, protocols and tools",
        "Art 7 – ICT systems, protocols and tools",
        "Art 8 – Identification of ICT risk",
        "Art 9 – Protection and prevention",
        "Art 10 – Detection of anomalous activities",
        "Art 11 – Response and recovery",
        "Art 12 – Backup policies and recovery procedures",
        "Art 13 – Learning and evolving",
        "Art 14 – Communication",
        "Art 17 – ICT-related incident management process",
        "Art 18 – Classification of ICT-related incidents",
        "Art 19 – Reporting of major ICT-related incidents",
        "Art 24 – General principles of digital operational resilience testing",
        "Art 26 – Advanced testing of ICT tools (TLPT)",
        "Art 28 – General principles on sound management of ICT third-party risk",
        "Art 30 – Key contractual provisions for ICT third-party service providers",
    ],
    "PCI DSS v4.0.1": [
        "Req 1 – Install and maintain network security controls",
        "Req 2 – Apply secure configurations to all system components",
        "Req 3 – Protect stored account data",
        "Req 4 – Protect cardholder data with strong cryptography during transmission over open, public networks",
        "Req 5 – Protect all systems and networks from malicious software",
        "Req 6 – Develop and maintain secure systems and software",
        "Req 7 – Restrict access to system components and cardholder data by business need to know",
        "Req 8 – Identify users and authenticate access to system components",
        "Req 9 – Restrict physical access to cardholder data",
        "Req 10 – Log and monitor all access to system components and cardholder data",
        "Req 11 – Test security of systems and networks regularly",
        "Req 12 – Support information security with organizational policies and programs",
    ],
}

# ── PDF extraction ────────────────────────────────────────────────────────────

def extract_pdf_text(uploaded_file) -> str:
    """Extract plain text from an uploaded PDF file."""
    reader = PdfReader(io.BytesIO(uploaded_file.read()))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages).strip()
    if not text:
        st.warning("Could not extract text from this PDF — it may be scanned/image-based. Try pasting the text manually.")
    return text

# ── Prompt builder ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are a senior GRC consultant specialising in information security compliance.
    You will be given a policy or control document and asked to perform a gap analysis
    against a specific framework.

    For EACH control domain / article provided, assess the input document and return
    a JSON array. Each element must have exactly these keys:

    - "domain"          : string  — the control domain/article label
    - "coverage"        : string  — one of: "Full", "Partial", "Missing"
    - "evidence"        : string  — quote or paraphrase from the document that supports
                                    coverage (or "None found" if missing)
    - "gap"             : string  — specific gap description (empty string if full coverage)
    - "risk_level"      : string  — one of: "High", "Medium", "Low", "N/A"
    - "recommendation"  : string  — concise remediation action (1–2 sentences)

    Return ONLY the JSON array. No markdown fences, no commentary.
""").strip()


def build_user_prompt(document: str, framework: str, domains: list[str]) -> str:
    domain_list = "\n".join(f"- {d}" for d in domains)
    return textwrap.dedent(f"""
        Framework: {framework}

        Control domains to assess:
        {domain_list}

        Document to analyse:
        ---
        {document}
        ---

        Return the gap analysis JSON array as instructed.
    """).strip()


# ── OpenAI call ───────────────────────────────────────────────────────────────

def run_gap_analysis(api_key: str, document: str, framework: str) -> list[dict]:
    client = openai.OpenAI(api_key=api_key)
    domains = FRAMEWORKS[framework]
    user_prompt = build_user_prompt(document, framework, domains)

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


# ── Helpers ───────────────────────────────────────────────────────────────────

RISK_COLOURS = {"High": "🔴", "Medium": "🟠", "Low": "🟡", "N/A": "⚪"}
COVERAGE_COLOURS = {"Full": "✅", "Partial": "🔶", "Missing": "❌"}
COVERAGE_RANK = {"Missing": 0, "Partial": 1, "Full": 2}
TREND_ICONS = {"Improved": "⬆️ Improved", "Regressed": "⬇️ Regressed", "Unchanged": "➡️ Unchanged"}


def score_summary(results: list[dict]) -> dict:
    total = len(results)
    full    = sum(1 for r in results if r["coverage"] == "Full")
    partial = sum(1 for r in results if r["coverage"] == "Partial")
    missing = sum(1 for r in results if r["coverage"] == "Missing")
    high    = sum(1 for r in results if r["risk_level"] == "High")
    pct     = round((full + 0.5 * partial) / total * 100) if total else 0
    return dict(total=total, full=full, partial=partial, missing=missing,
                high_risk=high, score=pct)


def results_to_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "Domain"        : r.get("domain", ""),
            "Coverage"      : f"{COVERAGE_COLOURS.get(r.get('coverage',''), '')} {r.get('coverage','')}",
            "Risk"          : f"{RISK_COLOURS.get(r.get('risk_level',''), '')} {r.get('risk_level','')}",
            "Gap"           : r.get("gap", ""),
            "Evidence"      : r.get("evidence", ""),
            "Recommendation": r.get("recommendation", ""),
        })
    return pd.DataFrame(rows)


def diff_results(results_v1: list[dict], results_v2: list[dict]) -> list[dict]:
    """Compare two gap-analysis result sets (same framework, same domains) and
    classify each domain as Improved / Regressed / Unchanged based on coverage."""
    by_domain_v2 = {r.get("domain"): r for r in results_v2}
    rows = []
    for r1 in results_v1:
        domain = r1.get("domain")
        r2 = by_domain_v2.get(domain)
        if r2 is None:
            continue
        rank1 = COVERAGE_RANK.get(r1.get("coverage"), 0)
        rank2 = COVERAGE_RANK.get(r2.get("coverage"), 0)
        if rank2 > rank1:
            trend = "Improved"
        elif rank2 < rank1:
            trend = "Regressed"
        else:
            trend = "Unchanged"
        rows.append({
            "domain": domain,
            "coverage_v1": r1.get("coverage", ""),
            "coverage_v2": r2.get("coverage", ""),
            "risk_v1": r1.get("risk_level", ""),
            "risk_v2": r2.get("risk_level", ""),
            "gap_v2": r2.get("gap", ""),
            "recommendation_v2": r2.get("recommendation", ""),
            "trend": trend,
        })
    return rows


def diff_summary(diff_rows: list[dict]) -> dict:
    improved  = sum(1 for r in diff_rows if r["trend"] == "Improved")
    regressed = sum(1 for r in diff_rows if r["trend"] == "Regressed")
    unchanged = sum(1 for r in diff_rows if r["trend"] == "Unchanged")
    return dict(improved=improved, regressed=regressed, unchanged=unchanged, total=len(diff_rows))


def diff_to_df(diff_rows: list[dict]) -> pd.DataFrame:
    rows = []
    for r in diff_rows:
        rows.append({
            "Domain"          : r["domain"],
            "Trend"           : TREND_ICONS.get(r["trend"], r["trend"]),
            "v1 Coverage"     : f"{COVERAGE_COLOURS.get(r['coverage_v1'], '')} {r['coverage_v1']}",
            "v2 Coverage"     : f"{COVERAGE_COLOURS.get(r['coverage_v2'], '')} {r['coverage_v2']}",
            "v2 Risk"         : f"{RISK_COLOURS.get(r['risk_v2'], '')} {r['risk_v2']}",
            "Remaining Gap (v2)": r["gap_v2"],
            "Recommendation (v2)": r["recommendation_v2"],
        })
    return pd.DataFrame(rows)


SAMPLE_DOCUMENT = textwrap.dedent("""
    Information Security Policy — Acme Ltd (v2.1)

    1. Access Control
    All systems require username and password authentication. Privileged accounts
    are reviewed quarterly. Remote access uses VPN with MFA enforced.

    2. Asset Management
    IT assets are inventoried in a CMDB updated monthly. Each asset has a named owner.
    Software licences are tracked centrally.

    3. Incident Response
    Security incidents must be reported to the SOC within 4 hours of detection.
    A post-incident review is conducted for P1/P2 events. There is no formal playbook
    for ransomware or data-exfiltration scenarios.

    4. Backup and Recovery
    Critical data is backed up daily to an off-site encrypted store.
    Recovery tests are conducted annually. RTO target is 24 hours.

    5. Vulnerability Management
    Internal networks are scanned monthly with an authenticated scanner.
    Critical patches must be applied within 14 days of release.
    There is currently no process for third-party/supply-chain vulnerability tracking.
""").strip()

SAMPLE_DOCUMENT_V2 = textwrap.dedent("""
    Information Security Policy — Acme Ltd (v3.0)

    1. Access Control
    All systems require username and password authentication, with MFA now enforced
    for all administrative access in addition to remote access. Privileged accounts
    are reviewed monthly.

    2. Asset Management
    IT assets are inventoried in a CMDB updated monthly. Each asset has a named owner.
    Software licences are tracked centrally. Third-party/supply-chain software components
    are now inventoried as part of the same CMDB process.

    3. Incident Response
    Security incidents must be reported to the SOC within 4 hours of detection.
    A post-incident review is conducted for P1/P2 events. A formal ransomware and
    data-exfiltration playbook was published this quarter, including containment
    steps and regulator notification timelines.

    4. Backup and Recovery
    Critical data is backed up weekly (reduced from daily due to storage cost
    optimisation) to an off-site encrypted store. Recovery tests are conducted
    annually. RTO target is 24 hours.

    5. Vulnerability Management
    Internal networks are scanned monthly with an authenticated scanner.
    Critical patches must be applied within 14 days of release. A quarterly
    third-party/supply-chain vulnerability review has been introduced, covering
    all vendors with system access.
""").strip()


def render_document_input(key_prefix: str, heading: str) -> str:
    """Renders the paste-text / upload-PDF input widget set for one document
    slot, using key_prefix to keep Streamlit widget state isolated when this
    is rendered more than once on the same page (e.g. v1 and v2 in compare mode)."""
    st.markdown(f"**{heading}**")

    input_method = st.radio(
        "Input method",
        ["Paste text", "Upload PDF"],
        horizontal=True,
        key=f"{key_prefix}_input_method",
        disabled=not PDF_SUPPORT,
        help="PDF upload requires `pypdf`. Install with: pip install pypdf" if not PDF_SUPPORT else None,
        label_visibility="collapsed",
    )

    document = ""

    if input_method == "Upload PDF":
        if not PDF_SUPPORT:
            st.warning("PDF support requires `pypdf`. Run `pip install pypdf` then restart the app.")
        else:
            uploaded_file = st.file_uploader(
                "Upload a policy or procedure document (PDF)",
                type=["pdf"],
                key=f"{key_prefix}_uploader",
                help="Text-based PDFs work best. Scanned/image PDFs may not extract correctly.",
            )
            if uploaded_file:
                with st.spinner("Extracting text from PDF..."):
                    document = extract_pdf_text(uploaded_file)
                if document:
                    st.success(f"Extracted {len(document):,} characters from {uploaded_file.name}")
                    with st.expander("Preview extracted text"):
                        st.text(document[:2000] + ("..." if len(document) > 2000 else ""))
    else:
        document = st.text_area(
            label="Policy / procedure / control description",
            height=240,
            key=f"{key_prefix}_textarea",
            placeholder=(
                "Paste the text of your information security policy, procedure, "
                "or control description here...\n\n"
                "Tip: even a partial draft works — the tool will flag what's missing."
            ),
            label_visibility="collapsed",
        )

    return document


# ── UI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Render the Streamlit app. Guarded by __main__ so this module can be
    imported for testing (e.g. pytest importing FRAMEWORKS, score_summary,
    diff_results) without executing any Streamlit UI calls."""

    st.title("🔒 GRC Gap Analyzer")
    st.caption(
        "Paste a security policy or control document — get an AI-powered gap analysis "
        "mapped to your chosen compliance framework."
    )

    # Sidebar — config
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Your key is used only for this session and never stored.",
        )
        framework = st.selectbox("Target Framework", list(FRAMEWORKS.keys()))
        st.markdown("---")
        st.markdown(
            "**Frameworks supported**\n"
            "- ISO 27001:2022 (Annex A)\n"
            "- NIST CSF 2.0\n"
            "- NIS2 Directive (Art 21–24)\n"
            "- DORA (Regulation EU 2022/2554)\n"
            "- PCI DSS v4.0.1 (12 requirements)\n\n"
            "**Model:** GPT-4o\n\n"
            "[GitHub](https://github.com/workmcg/grc-gap-ai) · "
            "[control-crosswalk](https://github.com/workmcg/control-crosswalk)"
        )

    mode_tab, compare_tab = st.tabs(["📄 Single document", "🔁 Compare two versions"])

    # ── Single document mode ───────────────────────────────────────────────────────
    with mode_tab:
        st.subheader("1 · Load your document")

        document = render_document_input("single", "Document")

        def _load_single_sample():
            st.session_state["single_textarea"] = SAMPLE_DOCUMENT

        st.button("Load sample document", type="secondary", key="single_sample", on_click=_load_single_sample)

        st.subheader("2 · Run analysis")
        run = st.button("Analyse", type="primary", disabled=not (api_key and document), key="single_run")

        if not api_key:
            st.info("Add your OpenAI API key in the sidebar to enable analysis.")
        elif not document:
            st.info("Paste a document above to get started.")

        if run and api_key and document:
            with st.spinner(f"Analysing against {framework} …"):
                try:
                    results = run_gap_analysis(api_key, document, framework)
                except json.JSONDecodeError:
                    st.error("The model returned an unexpected format. Try again or shorten your document.")
                    st.stop()
                except openai.AuthenticationError:
                    st.error("Invalid API key. Please check your OpenAI key in the sidebar.")
                    st.stop()
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
                    st.stop()

            st.subheader("3 · Results")

            s = score_summary(results)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Compliance Score", f"{s['score']}%")
            c2.metric("✅ Full Coverage",  s["full"])
            c3.metric("🔶 Partial",        s["partial"])
            c4.metric("❌ Missing",        s["missing"])
            c5.metric("🔴 High Risk Gaps", s["high_risk"])

            st.markdown("---")

            col_a, col_b = st.columns(2)
            filter_coverage = col_a.multiselect(
                "Filter by coverage",
                ["Full", "Partial", "Missing"],
                default=["Partial", "Missing"],
                key="single_filter_coverage",
            )
            filter_risk = col_b.multiselect(
                "Filter by risk level",
                ["High", "Medium", "Low", "N/A"],
                default=["High", "Medium"],
                key="single_filter_risk",
            )

            filtered = [
                r for r in results
                if r.get("coverage") in filter_coverage
                or r.get("risk_level") in filter_risk
            ]

            if not filtered:
                st.success("No gaps match the current filters — try adjusting the filter above.")
            else:
                df = results_to_df(filtered)
                st.dataframe(df, width="stretch", hide_index=True)

                csv = results_to_df(results).to_csv(index=False)
                st.download_button(
                    label="⬇ Export full report as CSV",
                    data=csv,
                    file_name=f"gap_analysis_{framework.split()[0].lower()}.csv",
                    mime="text/csv",
                    key="single_download",
                )

            with st.expander("Raw JSON output"):
                st.json(results)

    # ── Compare two versions mode ──────────────────────────────────────────────────
    with compare_tab:
        st.caption(
            "Run the same framework assessment against two versions of a document — "
            "e.g. last year's policy vs. this year's draft — and see which control "
            "domains improved, regressed, or stayed the same."
        )

        st.subheader("1 · Load both versions")
        col1, col2 = st.columns(2)
        with col1:
            document_v1 = render_document_input("v1", "Version 1 (baseline)")
        with col2:
            document_v2 = render_document_input("v2", "Version 2 (updated)")

        def _load_compare_sample():
            st.session_state["v1_textarea"] = SAMPLE_DOCUMENT
            st.session_state["v2_textarea"] = SAMPLE_DOCUMENT_V2

        st.button("Load sample v1 / v2 pair", type="secondary", key="compare_sample", on_click=_load_compare_sample)

        st.subheader("2 · Run comparison")
        compare_run = st.button(
            "Compare versions",
            type="primary",
            disabled=not (api_key and document_v1 and document_v2),
            key="compare_run",
        )

        if not api_key:
            st.info("Add your OpenAI API key in the sidebar to enable analysis.")
        elif not (document_v1 and document_v2):
            st.info("Load both a v1 and v2 document above to compare them.")

        if compare_run and api_key and document_v1 and document_v2:
            with st.spinner(f"Analysing both versions against {framework} …"):
                try:
                    results_v1 = run_gap_analysis(api_key, document_v1, framework)
                    results_v2 = run_gap_analysis(api_key, document_v2, framework)
                except json.JSONDecodeError:
                    st.error("The model returned an unexpected format. Try again or shorten your documents.")
                    st.stop()
                except openai.AuthenticationError:
                    st.error("Invalid API key. Please check your OpenAI key in the sidebar.")
                    st.stop()
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
                    st.stop()

            st.subheader("3 · Comparison results")

            diff_rows = diff_results(results_v1, results_v2)
            d = diff_summary(diff_rows)

            s1 = score_summary(results_v1)
            s2 = score_summary(results_v2)

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("v1 Score", f"{s1['score']}%")
            c2.metric("v2 Score", f"{s2['score']}%", delta=f"{s2['score'] - s1['score']:+d} pts")
            c3.metric("⬆️ Improved", d["improved"])
            c4.metric("⬇️ Regressed", d["regressed"])
            c5.metric("➡️ Unchanged", d["unchanged"])

            st.markdown("---")

            trend_filter = st.multiselect(
                "Filter by trend",
                ["Improved", "Regressed", "Unchanged"],
                default=["Improved", "Regressed"],
                key="compare_filter_trend",
            )

            filtered_diff = [r for r in diff_rows if r["trend"] in trend_filter]

            if not filtered_diff:
                st.success("No domains match the current filter — try adjusting it above.")
            else:
                diff_df = diff_to_df(filtered_diff)
                st.dataframe(diff_df, width="stretch", hide_index=True)

                csv = diff_to_df(diff_rows).to_csv(index=False)
                st.download_button(
                    label="⬇ Export comparison as CSV",
                    data=csv,
                    file_name=f"gap_comparison_{framework.split()[0].lower()}.csv",
                    mime="text/csv",
                    key="compare_download",
                )

            if d["regressed"] > 0:
                st.warning(
                    f"{d['regressed']} domain(s) regressed between versions — "
                    "worth a closer look before treating v2 as an improvement overall."
                )

            with st.expander("Raw JSON output (v1 / v2)"):
                st.json({"v1": results_v1, "v2": results_v2})


if __name__ == "__main__":
    main()
