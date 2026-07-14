# Automated Copywriting & Tone Transformer

A small pipeline that turns a raw product description into platform-specific
marketing copy using an LLM (Groq's free API).

## Project structure

```
copy_transformer/
├── models.py             # Data contracts (CopyRequest, CopyResponse)
├── prompt_compiler.py    # Builds the prompt from a request
├── client.py             # Talks to the Groq API
├── cli.py                # Command-line entry point
└── requirements.txt
```

Each file has one job:
- `models.py` defines what a request/response looks like and validates it
- `prompt_compiler.py` turns a request into an actual prompt, with
  platform-specific rules baked in
- `client.py` sends that prompt to Groq and returns the generated text
- `cli.py` is what you actually run — it reads your command-line arguments,
  builds a request, and calls the client

## Setup

1. Get a free Groq API key: https://console.groq.com/keys
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your API key as an environment variable:
   ```
   export GROQ_API_KEY="your-key-here"
   ```
   (On Windows: `set GROQ_API_KEY=your-key-here`)

## Running it

```
python3 cli.py --product "AquaPure Water Bottle" \
    --description "A self-cleaning water bottle with UV-C purification." \
    --platform instagram \
    --tone witty \
    --temperature 0.8
```

Options:
- `--product` (required) — product name
- `--description` (required) — raw product description
- `--platform` (required) — one of: linkedin, instagram, email
- `--tone` (default: professional) — e.g. witty, urgent, friendly
- `--temperature` (default: 0.7) — creativity, 0.0-2.0
- `--top-p` (default: 1.0) — nucleus sampling, 0.0-1.0
- `--max-tokens` (default: 400) — max response length

## Running in Google Colab

Colab doesn't give you a real folder by default, but you can still use this
exact structure by writing each file to disk with `%%writefile`, then
importing normally — this avoids any cell-ordering issues since imports
always re-read the file from disk.

Cell 1:
```
!pip install pydantic openai
```

Cell 2:
```
%%writefile models.py
<paste all of models.py here>
```

Cell 3:
```
%%writefile prompt_compiler.py
<paste all of prompt_compiler.py here>
```

Cell 4:
```
%%writefile client.py
<paste all of client.py here>
```

Cell 5:
```
import os
os.environ["GROQ_API_KEY"] = "your-key-here"
```

Cell 6:
```python
from models import CopyRequest
from client import generate_copy

req = CopyRequest(
    product_name="AquaPure Water Bottle",
    description="A self-cleaning water bottle with UV-C purification.",
    platform="instagram",
    tone="witty",
    temperature=0.8,
)
print(generate_copy(req))
```

Because `%%writefile` writes an actual `.py` file into Colab's filesystem,
`from models import CopyRequest` works exactly like it would on your own
computer — no import errors from things running out of order.
