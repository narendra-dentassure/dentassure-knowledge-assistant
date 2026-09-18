# DentAssure Knowledge Assistant

Local Streamlit chat for **[DentAssure Health Plans](https://dentassureplans.co.in/)**. It answers from sample policy documents (RAG) and from public DentAssure APIs (plans, clinics, compare). Runs on a laptop. No cloud URL. No login.

This repo is an **advanced RAG assistant** (hybrid retrieve, rerank, citations, refuse if unknown). It is not a document-workflow app and not a LangGraph multi-agent app.

| Who is asking | What they ask |
|---|---|
| Visitor / patient | Which plans exist, how to enroll, waiting periods, which plan for RCT + scaling, where is a clinic |
| Clinic front desk | Cashless steps, what to check before the chair, when to raise pre-auth |
| Claims desk | Renewal, annual limits, pre-auth — quoted from documents, not from memory |

1. [Run the app](#1-run-the-app)
2. [Type these questions](#2-type-these-questions)
3. [What you should see](#3-what-you-should-see)
4. [How one question is answered](#4-how-one-question-is-answered)
5. [Folders and modules](#5-folders-and-modules)
6. [Why this stack](#6-why-this-stack)
7. [Named use cases](#7-named-use-cases)
8. [Limits](#8-limits)
9. [What is in the ZIP](#9-what-is-in-the-zip)

---

## 1. Run the app

Unzip. Open a terminal **in this folder**.

```bash
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` and set `GEMINI_API_KEY`. Do not share that file.

```bash
python -m streamlit run app.py
```

Browser: **http://localhost:8501**

In a second terminal (no Gemini key needed):

```bash
python -m pytest tests -q
```

Optional: `python -m venv .venv` then `.venv\Scripts\activate` before `pip install`.  
If dentassureplans.co.in is blocked, set `PLATFORM_MODE=offline` in `.env`. Chat still works from `data/sample_docs` and `data/live_fixtures`.

---

## 2. Type these questions

Sidebar role: **Visitor**. Chat tab → copy each line. Pipeline trace under the answer shows **tool** (API) or document **sources** (RAG).

| # | Paste this | Pass if |
|---|---|---|
| 1 | `What are the key guidelines for DentAssure policy renewal?` | RAG. Cites `dentassure_policy_guide.pdf` (grace / T-30) |
| 2 | `How to take a DentAssure plan which is the best plan?` | RAG. No single “best” SKU. Mentions Secure / Shield / enroll |
| 3 | `What plans do you have?` | **API / fixture.** Lists featured plans |
| 4 | `STANDARD STEER - Explain about this plan` | **Plan-details API / fixture.** Price, limit, treatments, public URL |
| 5 | `Explain STANDARD SECURE waiting periods and coverage` | **RAG.** Cites `dentassure_plan_selection_guide.txt` |
| 6 | `SUPERIOR SPARKLE explain this plan` | **Ungrounded.** “Not in the provided documents” |
| 7 | `rct scaling konsa plan lena` | **Compare API / fixture.** Buy this: STANDARD STEER |
| 8 | `Where is a DentAssure clinic in Hyderabad and what are the hours and rating?` | **Clinic API / fixture.** Hours + rating |
| 9 | `What is the CEO's personal mobile number and home address?` | **Refuse.** No invented PII |

Then open tabs **Architecture** and **Observability**.

Same questions are listed under Chat → “Try these questions”, and as UC-01 … UC-11 on the **Use Cases** tab.

---

## 3. What you should see

| Capability | Where it is |
|---|---|
| 1 Load PDF, DOCX, TXT | `data/sample_docs/` — Documents tab |
| 2 Chunk → embed → Chroma | `src/ingest.py`, folder `storage/` (local, not in ZIP) |
| 3 Hybrid retrieve + rerank | BM25 + Chroma + RRF, then cross-encoder |
| 4 Conversation memory | Ask a follow-up after Q1 (grace period) |
| 5 Grounded citations | File name + page under the answer |
| 6 Missing info / injection | Q6 SPARKLE and Q9 CEO — refuse, do not invent |

Code quality:

| # | Expectation | In this repo |
|---|---|---|
| 1 | Functionality | Policy, clinic, catalog, plan page, compare, refuse |
| 2 | Modular structure | `app.py` + `src/application` + `src/domain` + `src/infrastructure` + `src/observability` + `tests/` |
| 3 | Meaningful naming | `rag_pipeline`, `hybrid_retriever`, `platform_tools` |
| 4 | No hard-coded secrets | `.env` / `.env.example` only |
| 5 | Errors and logging | try/except; `logs/app.log` + `logs/audit.jsonl` (git-ignored) |
| 6 | Docstrings | Modules and public functions |
| 7 | Refactor | Compact sample docs; no huge image PDFs |
| 8 | README | This file |
| 9 | Show understanding | Architecture tab + section 6 below |

Runs on this laptop. No hosted URL or extra monitoring service is required.

---

## 4. How one question is answered

```text
Role + question
        │
        ▼
 Guardrails (empty / too long / injection / CEO PII)
        │
        ├── "what plans"              → featured-plans API   (or fixture)
        ├── STEER / SHIELD / Smart Saver explain
        │                             → plan-details API     (or 3 fixtures)
        ├── RCT + scaling / konsa plan → compare-all-plans API (or fixture)
        ├── clinic / Hyderabad / hours → clinic list API     (or fixture)
        │
        ├── STANDARD SECURE / COMPLETE CARE / policy
        │                             → local RAG (PDF/DOCX/TXT) + citations
        │
        └── SPARKLE / CEO / unknown    → ungrounded refuse
```

**Roles change tone only, not facts.**  
Live APIs are used when the network works (`PLATFORM_MODE=auto`). If they fail, the same shape of answer comes from `data/live_fixtures/`.

Three plan paths:

| Question | Path | Why |
|---|---|---|
| Explain STANDARD STEER | Public plan page (API) | Current catalog SKU, price, treatments |
| Explain STANDARD SECURE | Documents (RAG) | Waiting table lives in the plan selection guide |
| Explain SUPERIOR SPARKLE | Refuse | Not in the 3 API slugs and not in sample docs |

---

## 5. Folders and modules

```text
app.py                         Streamlit UI
src/rag_pipeline.py            Guardrails → tools → else RAG
src/hybrid_retriever.py        BM25 + vectors + RRF
src/reranker.py                Cross-encoder
src/ingest.py                  Load → chunk → embed → Chroma
src/application/platform_tools.py   Catalog / plan page / clinic / compare
src/application/use_cases.py   UC-01 … UC-11
src/application/guardrails.py  Empty, injection, PII probe
src/application/roles.py       Visitor / Front Desk / Claims (tone)
src/infrastructure/dentassure_client.py   Public HTTP, no member token
src/observability/audit.py     One JSONL row per question
data/sample_docs/              2 PDF + 1 DOCX + 3 TXT
data/live_fixtures/            Offline API samples
tests/                         pytest, no Gemini call
.env.example                   Copy to .env
```

Sample documents (RAG):

- `dentassure_policy_guide.pdf` — renewal, limits, pre-auth
- `dentassure_member_handbook.pdf` — how to use a plan
- `dentassure_clinic_front_desk_sop.docx` — cashless at reception
- `dentassure_member_faq.txt`
- `dentassure_plan_selection_guide.txt` — STANDARD SECURE, SHIELD, Premium
- `dentassure_network_clinics.txt` — offline clinic directory

Public site the tools match: [Home](https://dentassureplans.co.in/) · [Our Plans](https://dentassureplans.co.in/our-plans) · [Network clinics](https://dentassureplans.co.in/our-network-clinics) · [All clinics](https://dentassureplans.co.in/all-clinics). Compare uses the public compare-all-plans API (no lead IDs stored).

---

## 6. Why this stack

Advanced RAG on a laptop: hybrid retrieve, rerank, grounded generate, refuse if unknown. Not a document-processing workflow. Not a LangGraph multi-agent graph.

The **model** is an LLM (Gemini). The **system** is a grounded assistant: guardrails → optional tools → else RAG. That is tool routing, not a multi-agent graph.

| Layer | Choice | Why | Why not |
|---|---|---|---|
| Language | Python 3.12 | Loaders, RAG, and tests in one runtime | Node/Java |
| UI | Streamlit `app.py` | One command to open the UI | FastAPI needs a separate frontend |
| LLM | Gemini Flash (OpenAI optional) | Generate only, key in `.env` | Heavy local models on a small laptop |
| Embeddings | MiniLM, local | No embedding API bill | OpenAI embeddings |
| Vector DB | Chroma on disk | Local folder, no cloud key | Pinecone = cloud |
| Retrieve | BM25 + Chroma + RRF | Exact words + meaning | Vector-only misses “T-30” |
| Rerank | Cross-encoder MiniLM | Retrieve then rerank before generate | Skipping rerank is basic RAG |
| Docs | pypdf + python-docx | PDF + DOCX + TXT | Image-only OCR PDFs fail offline |
| Tools | urllib to DentAssure public APIs | Real catalog/clinic/compare | LangChain / LangGraph multi-agent |
| Quality | pytest + JSONL audit | Tests need no billed key | Cloud APM |

---

## 7. Named use cases

Run from the **Use Cases** tab, or paste the question in Chat.

| ID | Scenario | Persona | Pass |
|---|---|---|---|
| UC-01 | Policy renewal | Claims Desk | Policy PDF, grace / T-30 |
| UC-02 | Pre-authorization | Claims Desk | RCT / Rs 12,000 |
| UC-03 | Annual limit / co-pay | Claims Desk | Plus vs Care |
| UC-04 | How to take a plan | Visitor | Selection guide, not a guessed SKU |
| UC-05 | Cashless at clinic | Front Desk | Front-desk SOP |
| UC-06 | Member FAQ | Visitor | Card, clinic, Customer Care |
| UC-07 | Follow-up | Visitor | Waiting period then pre-auth, still grounded |
| UC-08 | Clinic finder | Visitor | Hours / rating |
| UC-09 | Plan compare | Visitor | STANDARD STEER (or live rank) |
| UC-10 | Refuse | Visitor | No CEO phone |
| UC-11 | Featured plans | Visitor | Catalog, then STEER page; SPARKLE ungrounded |

`python -m pytest tests -q` checks chunking, hybrid retrieve, guardrails, memory, use-case catalog, and offline compare. It does **not** call Gemini.

---

## 8. Limits

- Compare ranks **lowest total out-of-pocket** for the named treatments. It is not full underwriting.
- Plan **API** details: STANDARD STEER, SUPERIOR SHIELD, Smart Saver only.
- Plan **RAG** details: STANDARD SECURE, COMPLETE CARE, Premium Dental Care.
- Other catalog names (SPARKLE) stay ungrounded on purpose — missing-info box.
- Public clinic cards often omit mobile numbers. Fallback: Customer Care **+91 888 668 6850**.
- Large Downloads brochures are image PDFs; useful facts were copied into the compact sample docs above. They are not in the ZIP (30–75 MB each).
- Use-case matching is keyword overlap, not an LLM router.

AI can make mistakes. Confirm a plan with DentAssure Customer Care **+91 888 668 6850**.

---

## 9. What is in the ZIP

**Included:** `app.py`, `src/`, `tests/`, `data/sample_docs/`, `data/live_fixtures/`, `requirements.txt`, `.env.example`, `README.md`, `pytest.ini`, `.streamlit/`, `scripts/`.

**Excluded:** `.env` (your key), `.venv/`, `storage/`, `logs/`, `__pycache__/`, `.git/`.

Rebuild: `powershell -File scripts/pack_submission.ps1` → `DentAssure_Knowledge_Assistant.zip`.
