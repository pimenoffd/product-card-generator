from product_cards.models import ProductCard
from product_cards.render import render_markdown


def test_render_includes_missing_spec_and_warnings():
    card = ProductCard(
        seo_title="Товар",
        seo_description="Текст",
        search_queries=["товар"],
        commercial_block="Данных нет",
        specs={"питание": None},
        missing_fields=["питание"],
        warnings=["Описание короткое"],
        status="needs_review",
    )
    result = render_markdown(card)
    assert "питание: данных нет" in result
    assert "Описание короткое" in result
    assert "needs_review" in result


def test_filename_uses_date_and_product_name():
    from datetime import datetime

    from product_cards.render import export_basename

    assert export_basename("Манометр DM/02", datetime(2026, 11, 6, 12, 34, 56)) == (
        "2026-11-06_12-34-56_Манометр_DM-02"
    )


def test_whitespace_spec_is_rendered_as_missing():
    card = ProductCard(
        seo_title="Товар",
        seo_description="Текст",
        search_queries=[],
        commercial_block="Текст",
        specs={"питание": "   "},
        missing_fields=["питание"],
        warnings=[],
        status="needs_review",
    )
    assert "питание: данных нет" in render_markdown(card)
