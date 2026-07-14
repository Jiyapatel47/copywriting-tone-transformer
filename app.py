"""
app.py

Streamlit web UI for the Automated Copywriting & Tone Transformer.

Two modes, as tabs:
  - Single: generate copy for one product (form-based)
  - Bulk (CSV): upload a CSV of many products, generate concurrently,
    watch live progress, view results in a table, download as CSV

Run with:
    streamlit run app.py
"""

import asyncio
import csv
import io
import time

import streamlit as st
from models import CopyRequest
from client import generate_copy
from bulk_processor import parse_csv_rows, run_bulk

st.set_page_config(
    page_title="Copywriting & Tone Transformer",
    page_icon="✍️",
    layout="centered",
)

PLATFORM_ICONS = {
    "instagram": "📸",
    "linkedin": "💼",
    "email": "✉️",
}

TONE_PRESETS = ["professional", "witty", "friendly", "urgent", "playful", "luxurious", "custom..."]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main .block-container { max-width: 820px; padding-top: 2rem; }

    .app-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .app-header h1 {
        font-size: 2.1rem;
        margin-bottom: 0.25rem;
    }
    .app-header p {
        color: rgba(250,250,250,0.6);
        font-size: 0.95rem;
    }

    .result-card {
        border: 1px solid rgba(250,250,250,0.15);
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        background: rgba(250,250,250,0.03);
        margin-top: 1rem;
    }
    .result-headline {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }
    .result-body {
        line-height: 1.6;
        white-space: pre-wrap;
    }
    .hashtag-row {
        margin-top: 1rem;
    }
    .hashtag-pill {
        display: inline-block;
        background: rgba(99, 102, 241, 0.18);
        color: rgb(165, 170, 250);
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        font-size: 0.85rem;
        margin: 0.15rem 0.25rem 0.15rem 0;
    }
    .platform-badge {
        display: inline-block;
        font-size: 0.8rem;
        color: rgba(250,250,250,0.55);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.5rem;
    }
    .row-success { color: rgb(110, 220, 150); }
    .row-failed { color: rgb(240, 120, 120); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-header">
        <h1>✍️ Copywriting & Tone Transformer</h1>
        <p>Turn a raw product description into platform-ready marketing copy.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar: advanced / inference settings (used by the Single tab)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Model Settings")
    st.caption("Controls how creative vs. consistent the output is. Applies to the Single tab.")

    temperature = st.slider(
        "Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1,
        help="Low = safe & consistent. High = creative & varied.",
    )
    top_p = st.slider(
        "Top-P", min_value=0.0, max_value=1.0, value=1.0, step=0.05,
        help="Narrows the pool of words the model can choose from.",
    )
    max_tokens = st.slider(
        "Max length (tokens)", min_value=50, max_value=1000, value=400, step=50,
        help="Roughly controls how long the generated copy can be.",
    )

    st.divider()
    st.caption("Quick presets:")
    preset_col1, preset_col2 = st.columns(2)
    with preset_col1:
        if st.button("🎯 Consistent", width="stretch"):
            st.session_state["temperature"] = 0.2
            st.session_state["top_p"] = 0.9
    with preset_col2:
        if st.button("🎨 Creative", width="stretch"):
            st.session_state["temperature"] = 1.0
            st.session_state["top_p"] = 1.0

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_single, tab_bulk = st.tabs(["✏️ Single", "📦 Bulk (CSV)"])

# ---------------------------------------------------------------------------
# TAB 1: Single generation
# ---------------------------------------------------------------------------
with tab_single:
    with st.form("copy_form"):
        product_name = st.text_input("Product name", placeholder="AquaPure Water Bottle")
        description = st.text_area(
            "Product description",
            placeholder="A self-cleaning water bottle with UV-C purification.",
            height=100,
        )

        col1, col2 = st.columns(2)
        with col1:
            platform = st.selectbox(
                "Platform",
                ["instagram", "linkedin", "email"],
                format_func=lambda p: f"{PLATFORM_ICONS[p]}  {p.capitalize()}",
            )
        with col2:
            tone_choice = st.selectbox("Tone", TONE_PRESETS)

        custom_tone = ""
        if tone_choice == "custom...":
            custom_tone = st.text_input("Custom tone", placeholder="e.g. nostalgic, bold, minimalist")

        submitted = st.form_submit_button("✨ Generate Copy", width="stretch")

    if submitted:
        final_tone = custom_tone.strip() if tone_choice == "custom..." else tone_choice

        if not product_name or not description:
            st.error("Please fill in both the product name and description.")
        elif tone_choice == "custom..." and not final_tone:
            st.error("Please enter a custom tone, or pick one of the presets.")
        else:
            try:
                req = CopyRequest(
                    product_name=product_name,
                    description=description,
                    platform=platform,
                    tone=final_tone,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                with st.spinner("Generating copy..."):
                    result = generate_copy(req)

                hashtags_html = ""
                if result.hashtags:
                    pills = "".join(f'<span class="hashtag-pill">#{tag}</span>' for tag in result.hashtags)
                    hashtags_html = f'<div class="hashtag-row">{pills}</div>'

                st.markdown(
                    f"""
                    <div class="result-card">
                        <div class="platform-badge">{PLATFORM_ICONS[platform]} {platform}</div>
                        <div class="result-headline">{result.headline}</div>
                        <div class="result-body">{result.body}</div>
                        {hashtags_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                download_text = result.headline + "\n\n" + result.body
                if result.hashtags:
                    download_text += "\n\n" + " ".join(f"#{tag}" for tag in result.hashtags)

                st.download_button(
                    "⬇️ Download as .txt",
                    download_text,
                    file_name=f"{product_name.replace(' ', '_').lower()}_{platform}_copy.txt",
                    width="stretch",
                )

            except ValueError as e:
                st.error(f"The model's output didn't match the expected format: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ---------------------------------------------------------------------------
# TAB 2: Bulk CSV generation
# ---------------------------------------------------------------------------
with tab_bulk:
    st.caption(
        "Upload a CSV with columns: **product_name, description, platform, tone** "
        "(optional: temperature, top_p, max_tokens). Every row is generated "
        "concurrently, capped by the concurrency limit below."
    )

    sample_csv = (
        "product_name,description,platform,tone\n"
        "AquaPure Water Bottle,A self-cleaning water bottle with UV-C purification,instagram,witty\n"
        "Stainless Lunchbox,Anime-style stainless steel lunchbox,linkedin,professional\n"
    )
    st.download_button(
        "⬇️ Download a sample CSV template",
        sample_csv,
        file_name="sample_products.csv",
        width="content",
    )

    uploaded_file = st.file_uploader("Upload products CSV", type=["csv"])
    concurrency = st.slider(
        "Concurrency (max requests in flight at once)",
        min_value=1, max_value=15, value=5,
        help="Higher = faster, but more likely to hit rate limits on the free tier.",
    )

    if uploaded_file is not None:
        csv_text = uploaded_file.getvalue().decode("utf-8")
        requests = parse_csv_rows(io.StringIO(csv_text))

        if not requests:
            st.error("No valid rows found in that CSV. Check the column names and try again.")
        else:
            st.success(f"Loaded {len(requests)} valid product(s) from the CSV.")
            with st.expander("Preview loaded products"):
                for r in requests:
                    st.write(f"- **{r.product_name}** → {PLATFORM_ICONS[r.platform]} {r.platform} ({r.tone})")

            if st.button("🚀 Generate All", width="stretch"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                completed = {"count": 0}

                def on_done(outcome: dict):
                    completed["count"] += 1
                    progress_bar.progress(completed["count"] / len(requests))
                    status_text.text(
                        f"{completed['count']}/{len(requests)} done -- "
                        f"last: {outcome['product_name']} ({outcome['status']})"
                    )

                start = time.time()
                results = asyncio.run(run_bulk(requests, concurrency, on_done=on_done))
                elapsed = time.time() - start

                succeeded = sum(1 for r in results if r["status"] == "success")
                failed = len(results) - succeeded
                status_text.empty()
                progress_bar.empty()

                if failed == 0:
                    st.success(f"Done in {elapsed:.1f}s -- all {succeeded} succeeded! 🎉")
                else:
                    st.warning(f"Done in {elapsed:.1f}s -- {succeeded} succeeded, {failed} failed.")

                st.dataframe(
                    [
                        {
                            "Product": r["product_name"],
                            "Platform": r["platform"],
                            "Status": "✅ success" if r["status"] == "success" else "❌ failed",
                            "Headline": r["headline"] or r["error"][:60],
                        }
                        for r in results
                    ],
                    width="stretch",
                )

                # Build a downloadable CSV of the full results (in-memory, no disk write)
                output_buffer = io.StringIO()
                fieldnames = ["product_name", "platform", "tone", "status", "headline", "body", "hashtags", "error"]
                writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)

                st.download_button(
                    "⬇️ Download full results as CSV",
                    output_buffer.getvalue(),
                    file_name="bulk_copy_results.csv",
                    width="stretch",
                )