# 🔒 GRC Gap Analyzer

AI-powered compliance gap analysis — paste a security policy or control document and get a structured gap report mapped to ISO 27001, NIST CSF 2.0, NIS2, DORA, or PCI DSS v4.0.1 in seconds. Also supports comparing two versions of a document to see whether compliance improved or regressed. Works with OpenAI, or with free-tier/local models (Groq, Google Gemini, Ollama) if you don't have OpenAI billing set up.

Built as a natural extension of [control-crosswalk](https://github.com/workmcg/control-crosswalk): where that tool maps controls statically across frameworks, this one uses LLM reasoning to assess *how well* a real document covers them.

---

## What it does

1. Pick a model provider (OpenAI, Groq, Google Gemini, or local Ollama) and paste in an API key if that provider needs one
2. Paste a policy/procedure, or upload a PDF directly
3. Select a target framework (ISO 27001:2022 · NIST CSF 2.0 · NIS2 · DORA · PCI DSS v4.0.1)
4. The model reads the document against every control domain and returns:
   - **Coverage** — Full / Partial / Missing
   - **Evidence** — the specific text that provides (or fails to provide) coverage
   - **Risk level** — High / Medium / Low
   - **Recommendation** — one actionable remediation step
5. Results render as a filterable table; export the full report to CSV

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

Open `http://localhost:8501`, pick a model provider in the sidebar, add an API key if needed, and run the built-in sample document to see it in action.

---

## Model providers

The app talks to all four providers through the same OpenAI-compatible chat completions API — only the endpoint, key, and model name change.

| Provider | Cost | Setup | Works on deployed Streamlit Cloud app? |
|---|---|---|---|
| OpenAI | Paid only, no free tier | [API key](https://platform.openai.com/api-keys) + billing | Yes |
| Groq | Free, no credit card | [Free API key](https://console.groq.com/keys) | Yes |
| Google Gemini | Free tier, daily quota | [Free API key](https://aistudio.google.com/apikey) | Yes |
| Ollama | Fully free, fully local | Install [Ollama](https://ollama.com), `ollama pull llama3.1` | **No** — local machine only |

A regular ChatGPT Plus/Pro subscription does **not** include OpenAI API credits — that's billed separately. If you don't want to pay for API usage, pick Groq or Gemini (both have a real, no-card-required free tier) or run Ollama locally for a fully offline, fully free setup.

The "Model" field in the sidebar is pre-filled with a sensible default per provider but can be overridden with any other model name that provider supports.

---

## Live demo

🔗 [grc-gap-analyzer.streamlit.app](https://grc-gap-analyzer.streamlit.app) — bring your own API key (OpenAI, Groq, or Gemini all work here; Ollama does not since it needs to run on your own machine). Nothing is stored server-side.

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
│   Model provider      │  ← OpenAI / Groq / Gemini / Ollama, all via the same
│   (OpenAI-compatible)  │    chat completions API; temperature 0.1 for
└────────┬────────────┘    consistent output (called twice in Compare mode)
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

**Why default to GPT-4o?** Structured JSON output is reliable at low temperature; the model handles long policy documents without chunking in most practical cases. Groq's Llama 3.3 70B and Gemini's Flash models are solid free alternatives for the same task.

**Why support four providers instead of just OpenAI?** OpenAI API access is paid-only with no free tier, which is a real barrier for anyone just wanting to try the tool. Groq, Gemini, and Ollama all expose an OpenAI-compatible chat completions API, so supporting them cost almost nothing in code (just a provider config + a `base_url` swap) for a large usability win.

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
- [x] Multi-provider support: Groq and Gemini free tiers, plus local Ollama

**Up next**
- [ ] Save/load past assessments without re-running the model
- [ ] PCI-DSS-style customized scope selection (only assess relevant SAQ requirements)

---

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

27 tests covering the framework and provider definitions, scoring and diff
logic (no API calls), plus Streamlit UI smoke tests using
`streamlit.testing.v1.AppTest` with the OpenAI client mocked — so the full
single-document and compare-versions flows are exercised for every provider
path without needing a real API key.

---

## Related

- **[control-crosswalk](https://github.com/workmcg/control-crosswalk)** — static cross-framework control mapping (ISO 27001 ↔ NIST CSF ↔ NIS2)

---

## License

MIT
