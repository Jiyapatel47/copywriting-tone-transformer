"""
client.py

The Model Client layer. Sends compiled prompts to Groq's OpenAI-compatible
API and returns a VALIDATED CopyResponse object -- not just raw text.

Includes automatic retry with exponential backoff + jitter for:
  - Transient API errors (rate limits, timeouts, connection issues)
  - Malformed model output (bad JSON, schema mismatch)

Groq requires a GROQ_API_KEY environment variable. Get one free at:
https://console.groq.com/keys
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI, APIError, APIConnectionError, RateLimitError
from pydantic import ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
from models import CopyRequest, CopyResponse
from prompt_compiler import build_messages

load_dotenv()  # reads GROQ_API_KEY from a .env file if present

MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("copy_transformer")

# Errors worth retrying: transient API problems, and cases where the model
# returned something that didn't parse/validate (often fixed by just asking
# again, since generation is non-deterministic).
RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APIError, ValueError)


def get_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable not set. "
            "Get a free key at https://console.groq.com/keys and run:\n"
            "  export GROQ_API_KEY='your-key-here'"
        )
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def get_async_client() -> AsyncOpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable not set. "
            "Get a free key at https://console.groq.com/keys and run:\n"
            "  export GROQ_API_KEY='your-key-here'"
        )
    return AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


@retry(
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    wait=wait_random_exponential(multiplier=1, max=20),  # 1s, 2s, 4s... + jitter, capped at 20s
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def generate_copy(req: CopyRequest) -> CopyResponse:
    """
    Send a CopyRequest to the model and return a VALIDATED CopyResponse.

    Uses the API's JSON mode so the model is constrained to return valid
    JSON, then validates that JSON against the CopyResponse schema with
    Pydantic. Automatically retries (up to 5 attempts, exponential backoff
    with jitter) on transient API errors or malformed/invalid output.
    """
    client = get_client()
    messages = build_messages(req)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
        response_format={"type": "json_object"},  # forces valid JSON output
    )
    raw_text = response.choices[0].message.content

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output: {raw_text}")

    try:
        return CopyResponse.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Model output did not match CopyResponse schema: {e}\nRaw output: {raw_text}")


def generate_copy_raw(req: CopyRequest) -> str:
    """
    Fallback: same as generate_copy but returns the raw text without JSON
    parsing/validation, and without retry logic. Useful for debugging what
    the model actually said.
    """
    client = get_client()
    messages = build_messages(req)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
    )
    return response.choices[0].message.content


@retry(
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    wait=wait_random_exponential(multiplier=1, max=20),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def generate_copy_async(req: CopyRequest) -> CopyResponse:
    """
    Async version of generate_copy, for use in concurrent/bulk pipelines
    (e.g. processing many CSV rows at once with asyncio.gather). Same
    validation and retry behavior as the synchronous version.
    """
    client = get_async_client()
    messages = build_messages(req)

    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
        response_format={"type": "json_object"},
    )
    raw_text = response.choices[0].message.content

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output: {raw_text}")

    try:
        return CopyResponse.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Model output did not match CopyResponse schema: {e}\nRaw output: {raw_text}")
