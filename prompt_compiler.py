"""
prompt_compiler.py

The "Master Instruction Template" layer.

Takes a validated CopyRequest and compiles it into a system prompt + user
prompt pair. Platform-specific rules live here, hidden from the end user,
so raw input is always sandboxed inside a controlled structure before it
ever reaches the model.
"""

from models import CopyRequest


# Platform-specific constraints. Add new platforms here without touching
# any other part of the pipeline.
PLATFORM_RULES = {
    "linkedin": (
        "Write in a professional, thought-leadership tone. "
        "3-5 short paragraphs. No emojis. End with a soft question that "
        "invites engagement. Target length: 100-200 words."
    ),
    "instagram": (
        "Write a casual, punchy caption. Maximum 150 words. "
        "Include 3-5 relevant hashtags at the end, separated by spaces. "
        "Emojis are welcome and encouraged."
    ),
    "email": (
        "Write a formal marketing email. Include a subject line on the "
        "first line prefixed with 'Subject:', followed by a blank line, "
        "then the email body. Include one clear call-to-action near the end."
    ),
}


SYSTEM_PROMPT = """You are a professional marketing copywriter working for a brand \
that values clarity and authenticity. You always follow the platform-specific \
formatting rules exactly. You never invent facts about the product that were \
not provided to you."""


def build_user_prompt(req: CopyRequest) -> str:
    """Compile a CopyRequest into the user-turn prompt string."""
    rules = PLATFORM_RULES[req.platform]

    return f"""Product name: {req.product_name}
Product description: {req.description}
Target platform: {req.platform}
Requested tone: {req.tone}

Platform rules you must follow:
{rules}

Respond with ONLY a valid JSON object (no markdown fences, no preamble, no \
explanation) with exactly these fields:
{{
  "platform": "{req.platform}",
  "headline": "a short attention-grabbing headline or subject line",
  "body": "the main copy text, following the platform rules above",
  "hashtags": ["list", "of", "hashtags", "without", "the", "hash", "symbol"]
}}

For platforms other than instagram, return an empty list for hashtags."""


def build_messages(req: CopyRequest) -> list[dict]:
    """Return the full chat messages array ready to send to the API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(req)},
    ]
