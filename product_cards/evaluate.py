"""Evaluate saved cards or explicitly run a small live benchmark."""

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from product_cards.llm import GenerationError, request_copy
from product_cards.models import ProductCard, ProductInput
from product_cards.service import generate_card, validate_copy


# This is a review heuristic: it cannot verify units, meaning, or correct attribution.
def numbers(text: str) -> set[str]:
    return {value.replace(",", ".") for value in re.findall(r"\d+(?:[.,]\d+)?", text)}


def assess(product: ProductInput, card: ProductCard) -> dict:
    source = product.model_dump_json()
    generated = " ".join(
        [card.seo_title, card.seo_description, card.commercial_block, *card.search_queries]
    )
    return {
        "format_issues": validate_copy(card),
        "specs_preserved": card.specs == product.specs,
        "unsupported_numbers": sorted(numbers(generated) - numbers(source)),
        "service_text_detected": bool(
            re.search(
                r"данных (?:нет|недостаточно|не хватает)|входны[ех] данны|"
                r"характеристики .*отсутствуют|отсутствие данных|обратит(?:есь|ься) к|"
                r"если .*предоставлен",
                generated,
                re.I,
            )
        ),
        "metadata": card.metadata.model_dump(mode="json") if card.metadata else None,
        "manual_review": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("evals/cases.json"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--results", type=Path, help="JSON object mapping case IDs to saved cards")
    source.add_argument("--live", action="store_true", help="Call OpenRouter; consumes API credits")
    parser.add_argument("--output", type=Path, default=Path("evals/reports/report.json"))
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    saved = json.loads(args.results.read_text(encoding="utf-8")) if args.results else {}
    if args.live:
        load_dotenv(".env")
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if args.live and (not key or not model):
        parser.error("Set OPENROUTER_API_KEY and OPENROUTER_MODEL in .env")
    report = {
        "mode": "live" if args.live else "saved",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "cases": [],
    }
    errors = False
    with httpx.Client() as client:
        for index, case in enumerate(cases, start=1):
            row = {"id": case["id"]}
            print(f"[{index}/{len(cases)}] {case['id']}: processing", flush=True)
            try:
                product = ProductInput.model_validate(case["input"])
                if args.live:
                    card = generate_card(
                        product,
                        request=lambda p, issues: request_copy(
                            p, issues=issues, client=client, api_key=key, model=model
                        ),
                    )
                elif case["id"] in saved:
                    card = ProductCard.model_validate(saved[case["id"]])
                else:
                    row["error"] = "No saved result for this case"
                    errors = True
                    report["cases"].append(row)
                    print(f"[{index}/{len(cases)}] {case['id']}: {row['error']}", flush=True)
                    continue
                row["assessment"] = assess(product, card)
                row["result"] = card.model_dump(mode="json")
            except GenerationError as exc:
                row["error"] = str(exc)
                errors = True
            except ValidationError:
                row["error"] = "Invalid input or saved card schema"
                errors = True
            report["cases"].append(row)
            status = f"error: {row['error']}" if "error" in row else "done"
            print(f"[{index}/{len(cases)}] {case['id']}: {status}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Report saved to {args.output}; {len(cases)} cases; errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
