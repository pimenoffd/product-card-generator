from collections.abc import Callable
from datetime import datetime, timezone
from time import perf_counter

from product_cards.llm import PROMPT_HASH, PROMPT_VERSION
from product_cards.models import (
    GeneratedCopy,
    GenerationMetadata,
    GenerationResponse,
    ProductCard,
    ProductInput,
    TokenUsage,
)


def validate_copy(copy: GeneratedCopy) -> list[str]:
    issues = []
    if not 1 <= len(copy.seo_title.strip()) <= 70:
        issues.append("Заголовок должен содержать от 1 до 70 символов.")
    length = len(copy.seo_description.strip())
    if not 800 <= length <= 1200:
        issues.append(f"Описание содержит {length} символов; требуется 800–1200.")
    queries = [q.strip() for q in copy.search_queries]
    if (
        not 3 <= len(queries) <= 5
        or any(not q for q in queries)
        or len({q.casefold() for q in queries}) != len(queries)
    ):
        issues.append("Требуется от 3 до 5 непустых различных поисковых запросов.")
    if not copy.commercial_block.strip():
        issues.append("Отсутствует commercial-блок.")
    return issues


def generate_card(
    product: ProductInput, *, request: Callable[[ProductInput, list[str]], GenerationResponse]
) -> ProductCard:
    started = perf_counter()
    responses = [request(product, [])]
    copy = responses[-1].content
    issues = validate_copy(copy)
    if issues:
        # Retry once with the original facts and the specific validation failures.
        responses.append(request(product, issues))
        copy = responses[-1].content
        issues = validate_copy(copy)
    missing = []
    if not product.manufacturer or not product.manufacturer.strip():
        missing.append("Производитель")
    if not product.description or not product.description.strip():
        missing.append("Описание и назначение")
    if not product.specs:
        missing.append("Характеристики")
    for key, value in product.specs.items():
        if value is None or not value.strip():
            missing.append(key)
    # Preserve technical specifications from the input instead of generating them.
    return ProductCard(
        **copy.model_dump(),
        specs=product.specs,
        missing_fields=missing,
        warnings=issues,
        status="needs_review" if issues or missing else "valid",
        metadata=GenerationMetadata(
            generated_at=datetime.now(timezone.utc),
            duration_seconds=round(perf_counter() - started, 3),
            attempts=len(responses),
            models=[r.model for r in responses],
            prompt_version=PROMPT_VERSION,
            prompt_hash=PROMPT_HASH,
            usage=TokenUsage(
                prompt_tokens=sum_usage(responses, "prompt_tokens"),
                completion_tokens=sum_usage(responses, "completion_tokens"),
            ),
        ),
    )


def sum_usage(responses: list[GenerationResponse], field: str) -> int | None:
    values = [getattr(r.usage, field) for r in responses]
    return sum(values) if all(v is not None for v in values) else None
