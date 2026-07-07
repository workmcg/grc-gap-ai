# 🔒 GRC Gap Analyzer

AI-powered compliance gap analysis — paste a security policy or control document and get a structured gap report mapped to ISO 27001, NIST CSF 2.0, NIS2, or DORA in seconds.

Built as a natural extension of [control-crosswalk](https://github.com/workmcg/control-crosswalk): where that tool maps controls statically across frameworks, this one uses LLM reasoning to assess *how well* a real document covers them.

---

## What it does

1. Paste a policy/procedure, or upload a PDF directly
2. Select a target framework (ISO 27001:2022 · NIST CSF 2.0 · NIS2 · DORA)
3. GPT-4o reads the document against every control domain and returns:
   - **Coverage** — Full / Partial / Missing
   - **Evidence** — the specific text that provides (or fails to provide) coverage
   - **Risk level** — High / Medium / Low
   - **Recommendation** — one actionable remediation step
4. Results render as a filterable table; export the full report to CSV

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

🚧 Not yet deployed — currently local-only. Streamlit Community Cloud deployment is next on the roadmap.

---

## Frameworks supported

| Framework | Version | Controls assessed |
|---|---|---|
| ISO/IEC 27001 | 2022 (Annex A) | 36 control domains |
| NIST CSF | 2.0 | 22 subcategories |
| NIS2 Directive | 2022/2555 | 12 articles (Art 21–24) |
| DORA | Regulation (EU) 2022/2554 | 17 articles |

---

## Architecture

```
┌─────────────────────┐
│   Streamlit UI       │  ← text input, framework picker, filter, CSV export
└────────┬────────────┘
         │ document + framework domains
         ▼
┌─────────────────────┐
│   Prompt builder     │  ← structured system prompt + per-domain instructions
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   OpenAI GPT-4o       │  ← temperature 0.1 for consistent, auditable output
└────────┬────────────┘
         │ JSON array
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

**Up next**
- [ ] Live deployment on Streamlit Community Cloud
- [ ] Multi-document comparison (e.g. compare v1 vs v2 of a policy)
- [ ] PCI-DSS v4.0 framework
- [ ] Local model support (Ollama / llama.cpp) for air-gapped environments

---

## Related

- **[control-crosswalk](https://github.com/workmcg/control-crosswalk)** — static cross-framework control mapping (ISO 27001 ↔ NIST CSF ↔ NIS2)

---

## License

MIT
