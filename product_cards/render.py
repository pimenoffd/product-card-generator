import re
from datetime import datetime

from product_cards.models import ProductCard


def export_basename(name: str, timestamp: datetime) -> str:
    safe_name = re.sub(r"[^\w.-]+", "-", name.strip().replace(" ", "_"))
    safe_name = safe_name.strip("._-")[:100] or "product"
    return f"{timestamp:%Y-%m-%d_%H-%M-%S}_{safe_name}"


def render_markdown(card: ProductCard) -> str:
    specs = (
        "\n".join(
            f"- {key}: {value if value and value.strip() else 'данных нет'}"
            for key, value in card.specs.items()
        )
        or "Данных нет"
    )
    queries = "\n".join(f"- {q}" for q in card.search_queries)
    warnings = "\n".join(f"- {w}" for w in card.warnings + card.missing_fields) or "Замечаний нет."
    return (
        f"# {card.seo_title}\n\n## Описание\n\n{card.seo_description}\n\n"
        f"## Характеристики\n\n{specs}\n\n## Поисковые запросы\n\n{queries}\n\n"
        f"## Для менеджера\n\n{card.commercial_block}\n\n"
        f"## Проверка: {card.status}\n\n{warnings}\n"
    )
