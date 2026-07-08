# 🔒 GRC Gap Analyzer

AI-powered compliance gap analysis — paste a security policy or control document and get a structured gap report mapped to ISO 27001, NIST CSF 2.0, NIS2, DORA, or PCI DSS v4.0.1 in seconds. Also supports comparing two versions of a document to see whether compliance improved or regressed.

Built as a natural extension of [control-crosswalk](https://github.com/workmcg/control-crosswalk): where that tool maps controls statically across frameworks, this one uses LLM reasoning to assess *how well* a real document covers them.

---

## What it does

1. Paste a policy/procedure, or upload a PDF directly
2. Select a target framework (ISO 27001:2022 · NIST CSF 2.0 · NIS2 · DORA · PCI DSS v4.0.1)
3. GPT-4o reads the document against every control domain and returns:
   - **Coverage** — Full / Partial / Missing
   - **Evidence** — the specific text that provides (or fails to provide) coverage
   - **Risk level** — High / Medium / Low
   - **Recommendation** — one actionable remediation step
4. Results render as a filterable table; export the full report to CSV

There's a second mode too: **Compare two versions**. Load a v1 (baseline) and v2
(updated) document side by side, run the same framework assessment against both,
and get a per-domain diff showing which control areas improved, regressed, or
stayed the same — useful for tracking whether a policy rewrite actually closed
the gaps it was meant to, or quietly introduced new ones.

![Screenshot placeholder](docs/screenshot.png)

---

## Quick start

```bash
git clone https://github.com/workmcg/grc-gap-ai
cd grc-gap-ai
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`, add your OpenAI API key in the sidebar, and run the built-in sample document to see it in action.

---

## Live demo

🔗 [grc-gap-analyzer.streamlit.app](https://grc-gap-analyzer.streamlit.app) — bring your own OpenAI API key, nothing is stored server-side.

---

## Frameworks supported

| Framework | Version | Controls assessed |
|---|---|---|
| ISO/IEC 27001 | 2022 (Annex A) | 37 control domains |
| NIST CSF | 2.0 | 22 subcategories |
| NIS2 Directive | 2022/2555 | 12 articles (Art 21–24) |
| DORA | Regulation (EU) 2022/2554 | 17 articles |
| PCI DSS | v4.0.1 | 12 principal requirements |

---

## Architecture

```
┌─────────────────────┐
│   Streamlit UI       │  ← text input (single or v1/v2 pair), framework picker,
└────────┬────────────┘    filter, CSV export
         │ document(s) + framework domains
         ▼
┌─────────────────────┐
│   Prompt builder     │  ← structured system prompt + per-domain instructions
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   OpenAI GPT-4o       │  ← temperature 0.1 for consistent, auditable output
└────────┬────────────┘    (called twice in Compare mode: once per version)
         │ JSON array(s)
         ▼
┌─────────────────────┐
│   Scoring / diff      │  ← score_summary() for single-doc mode,
│   engine               │    diff_results() classifies each domain as
└────────┬────────────┘    Improved / Regressed / Unchanged in Compare mode
         │
         ▼
┌─────────────────────┐
│   pandas DataFrame    │  ← scored, filtered, colour-coded, exportable
└─────────────────────┘
```

---

## Design decisions

**Why GPT-4o?** Structured JSON output is reliable at low temperature; the model handles long policy documents without chunking in most practical cases.

**Why Streamlit?** Zero-JS, Python-native, free deployment on Community Cloud — gets a shareable demo live in under 5 minutes.

**Why not store the API key server-side?** The tool is designed for individual use. Keeping the key in the sidebar means no server-side secrets management and no accidental key exposure in a shared deployment.

---

## Roadmap

**Shipped**
- [x] PDF upload support (via `pypdf`)
- [x] DORA (Digital Operational Resilience Act) framework
- [x] Multi-document comparison (compare v1 vs v2 of a policy)
- [x] PCI DSS v4.0.1 framework
- [x] Live deployment on Streamlit Community Cloud

**Up next**
- [ ] Local model support (Ollama / llama.cpp) for air-gapped environments
- [ ] Save/load past assessments without re-running the model

---

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

19 tests covering the framework definitions, scoring and diff logic (no API
calls), plus Streamlit UI smoke tests using `streamlit.testing.v1.AppTest`
with the OpenAI client mocked — so the full single-document and
compare-versions flows are exercised without needing a real API key.

---

## Related

- **[control-crosswalk](https://github.com/workmcg/control-crosswalk)** — static cross-framework control mapping (ISO 27001 ↔ NIST CSF ↔ NIS2)

---

## License

MIT
