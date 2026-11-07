from product_cards.llm import PROMPT_HASH, PROMPT_VERSION
from product_cards.models import GeneratedCopy, GenerationResponse, ProductInput, TokenUsage
from product_cards.service import generate_card


def test_metadata_accumulates_both_attempts():
    calls = []

    def request(product, issues):
        calls.append(issues)
        return GenerationResponse(
            content=GeneratedCopy(
                seo_title="Товар",
                seo_description="Коротко",
                search_queries=["один", "два", "три"],
                commercial_block="Назначение",
            ),
            model="actual-model",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
        )

    card = generate_card(ProductInput(name="Товар"), request=request)
    assert card.metadata.attempts == 2
    assert card.metadata.models == ["actual-model", "actual-model"]
    assert card.metadata.usage.prompt_tokens == 20
    assert card.metadata.usage.completion_tokens == 40
    assert card.metadata.prompt_version == PROMPT_VERSION
    assert card.metadata.prompt_hash == PROMPT_HASH
    assert card.metadata.generated_at.tzinfo is not None
    assert card.metadata.duration_seconds >= 0


def test_missing_token_usage_is_unknown():
    response = GenerationResponse(
        content=GeneratedCopy(
            seo_title="Товар",
            seo_description="а" * 800,
            search_queries=["один", "два", "три"],
            commercial_block="Назначение",
        ),
        model="test",
    )
    card = generate_card(ProductInput(name="Товар"), request=lambda p, i: response)
    assert card.metadata.attempts == 1
    assert card.metadata.usage.prompt_tokens is None
