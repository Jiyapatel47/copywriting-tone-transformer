"""
cli.py

The entry point / ingestion layer. Parses command-line arguments into a
CopyRequest, then runs it through the pipeline.

Usage:
    python3 cli.py --product "AquaPure Water Bottle" \\
        --description "A self-cleaning water bottle with UV-C purification." \\
        --platform instagram --tone witty --temperature 0.8
"""

import argparse
from models import CopyRequest
from client import generate_copy


def parse_args() -> CopyRequest:
    parser = argparse.ArgumentParser(
        description="Generate marketing copy from a product description."
    )
    parser.add_argument("--product", required=True, help="Product name")
    parser.add_argument("--description", required=True, help="Raw product description")
    parser.add_argument(
        "--platform",
        required=True,
        choices=["linkedin", "instagram", "email"],
        help="Target platform",
    )
    parser.add_argument(
        "--tone", default="professional", help="Desired tone, e.g. witty, urgent"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.7, help="Creativity (0.0-2.0)"
    )
    parser.add_argument(
        "--top-p", type=float, default=1.0, help="Nucleus sampling parameter (0.0-1.0)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=400, help="Maximum length of the response"
    )

    args = parser.parse_args()

    return CopyRequest(
        product_name=args.product,
        description=args.description,
        platform=args.platform,
        tone=args.tone,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    )


def main():
    request = parse_args()
    print("Generating copy...\n")
    try:
        result = generate_copy(request)
    except ValueError as e:
        print(f"Generation failed validation: {e}")
        return

    print("=== GENERATED COPY ===")
    print(f"Headline: {result.headline}\n")
    print(result.body)
    if result.hashtags:
        print("\n" + " ".join(f"#{tag}" for tag in result.hashtags))


if __name__ == "__main__":
    main()
