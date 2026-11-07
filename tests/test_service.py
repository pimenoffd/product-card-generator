from product_cards.models import GeneratedCopy, GenerationResponse, ProductInput
from product_cards.service import generate_card


def test_valid_card_preserves_specs():
    product = ProductInput(
        name="Прибор",
        manufacturer="Завод",
        description="Измеряет давление",
        specs={"диапазон": "0–1,6 МПа"},
    )
    copy = GeneratedCopy(
        seo_title="Прибор",
        seo_description="а" * 800,
        search_queries=["один", "два", "три"],
        commercial_block="Для измерения давления",
    )
    result = generate_card(
        product, request=lambda product, issues: GenerationResponse(content=copy, model="test")
    )
    assert result.status == "valid"
    assert result.specs == product.specs


def test_short_description_warns_after_one_retry():
    calls = []

    def request(product, issues):
        calls.append(issues)
        return GenerationResponse(
            model="test",
            content=GeneratedCopy(
                seo_title="Прибор",
                seo_description="Кратко",
                search_queries=["один", "два", "три"],
                commercial_block="Данных нет",
            ),
        )

    result = generate_card(ProductInput(name="Прибор"), request=request)
    assert len(calls) == 2
    assert result.status == "needs_review"
    assert result.warnings


def test_empty_fields_are_reported_as_missing():
    copy = GeneratedCopy(
        seo_title="Прибор",
        seo_description="а" * 800,
        search_queries=["один", "два", "три"],
        commercial_block="Данных нет",
    )
    product = ProductInput(name="Прибор", manufacturer=" ", description="", specs={"питание": " "})
    result = generate_card(
        product, request=lambda product, issues: GenerationResponse(content=copy, model="test")
    )
    assert result.status == "needs_review"
    assert set(result.missing_fields) == {"Производитель", "Описание и назначение", "питание"}


def test_length_boundaries():
    from product_cards.service import validate_copy

    for title_length, description_length, valid in [
        (70, 800, True),
        (70, 1200, True),
        (71, 800, False),
        (70, 799, False),
        (70, 1201, False),
    ]:
        copy = GeneratedCopy(
            seo_title="а" * title_length,
            seo_description="а" * description_length,
            search_queries=["один", "два", "три"],
            commercial_block="Назначение",
        )
        assert (not validate_copy(copy)) is valid
