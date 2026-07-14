# ✍️ Automated Copywriting & Tone Transformer

A small pipeline that turns a raw product description into platform-specific,
schema-validated marketing copy using an LLM (Groq's free API) — with a CLI,
a bulk CSV processor, and a full web UI.

## Project structure

```
copy_transformer_project/
├── models.py             # Data contracts (CopyRequest, CopyResponse)
├── prompt_compiler.py    # Builds the prompt from a request (platform rules)
├── client.py             # Talks to Groq (sync + async, retry, validation)
├── cli.py                # Command-line entry point (single product)
├── bulk_processor.py     # CSV bulk generation with async concurrency
├── app.py                # Streamlit web UI (Single + Bulk tabs)
├── requirements.txt
├── sample_products.csv   # Example input for bulk mode
├── .env.example           # Template for your API key
└── .gitignore
```

Each file has one job:
- **`models.py`** — defines what a request/response looks like (`CopyRequest`,
  `CopyResponse`) and validates it with Pydantic.
- **`prompt_compiler.py`** — turns a request into an actual prompt, with
  platform-specific rules (LinkedIn / Instagram / Email) baked in. Asks the
  model to return structured JSON matching `CopyResponse`.
- **`client.py`** — sends the prompt to Groq and validates the JSON response
  against the `CopyResponse` schema. Includes automatic retry with
  exponential backoff + jitter on transient errors or malformed output.
  Has both a synchronous (`generate_copy`) and async (`generate_copy_async`)
  version.
- **`cli.py`** — terminal entry point for one product at a time.
- **`bulk_processor.py`** — reads a CSV of many products, generates copy for
  all of them **concurrently** (capped by a semaphore to avoid rate limits),
  and writes results to an output CSV.
- **`app.py`** — Streamlit web UI with two tabs: **Single** (form-based, one
  product) and **Bulk (CSV)** (upload a CSV, watch a live progress bar,
  download results).

## Setup

1. Get a free Groq API key: https://console.groq.com/keys
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your API key:
   - Rename `.env.example` to `.env`
   - Open it and replace the placeholder with your real key:
     ```
     GROQ_API_KEY=your-actual-key-here
     ```

## Running it

### Web UI (recommended)

```
streamlit run app.py
```
Opens in your browser automatically. Use the **Single** tab for one product,
or the **Bulk (CSV)** tab to upload a CSV and generate many at once with a
live progress bar.

### Command line — single product

```
python cli.py --product "AquaPure Water Bottle" \
    --description "A self-cleaning water bottle with UV-C purification." \
    --platform instagram \
    --tone witty \
    --temperature 0.8
```

Options:
- `--product` (required) — product name
- `--description` (required) — raw product description
- `--platform` (required) — one of: `linkedin`, `instagram`, `email`
- `--tone` (default: professional) — e.g. witty, urgent, friendly
- `--temperature` (default: 0.7) — creativity, 0.0–2.0
- `--top-p` (default: 1.0) — nucleus sampling, 0.0–1.0
- `--max-tokens` (default: 400) — max response length

### Command line — bulk CSV

```
python bulk_processor.py --input sample_products.csv --output results.csv --concurrency 5
```

Input CSV needs columns: `product_name, description, platform, tone`
(optionally `temperature, top_p, max_tokens`). Output CSV includes a
`status`/`error` column per row so failures are visible without stopping
the whole batch.

## How data flows

```
User input (CLI args, Streamlit form, or CSV row)
        ↓
   models.py          → validates input into a CopyRequest
        ↓
prompt_compiler.py    → compiles a platform-aware prompt, requests JSON output
        ↓
   client.py          → calls Groq, validates response into a CopyResponse
                         (auto-retries on failure/malformed output)
        ↓
cli.py / app.py / bulk_processor.py   → displays or writes the result
```

## Key engineering features

- **Dynamic prompt compilation** — platform rules (LinkedIn/Instagram/Email)
  injected via f-strings, isolated from raw user input.
- **Inference parameter tuning** — temperature and top-p exposed and passed
  straight through to the API.
- **Schema-validated output** — model responses are parsed as JSON and
  validated against a Pydantic schema before being trusted.
- **Resilience** — automatic retry with exponential backoff + jitter on
  transient API errors or malformed output.
- **Concurrency** — bulk CSV jobs run with `asyncio.gather` + a `Semaphore`
  to process many requests in parallel without exceeding rate limits.

## Notes

- Uses Groq's free, OpenAI-compatible API (`llama-3.3-70b-versatile`) rather
  than OpenAI directly — same client library, different `base_url`.
- Never commit your real `.env` file — it's excluded via `.gitignore`.