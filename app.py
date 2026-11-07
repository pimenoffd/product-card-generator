import json
import os
from datetime import datetime

import httpx
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from product_cards.llm import GenerationError, request_copy
from product_cards.models import ProductInput
from product_cards.render import export_basename, render_markdown
from product_cards.service import generate_card

load_dotenv()
st.title("Генератор карточек товаров")
st.caption("Черновик необходимо проверить по исходным данным перед публикацией.")
example = {
    "name": "Манометр показывающий DM 02",
    "manufacturer": "Манотомь",
    "specs": {
        "диапазон измерений": "0–1,6 МПа",
        "класс точности": "1,5",
        "присоединение": "G1/2",
        "диаметр корпуса": "100 мм",
    },
    "description": "Прибор предназначен для измерения избыточного давления.",
}
with st.form("product"):
    raw = st.text_area(
        "Данные товара (JSON)", value=json.dumps(example, ensure_ascii=False, indent=2), height=300
    )
    submitted = st.form_submit_button("Создать карточку")
if submitted:
    st.session_state.pop("card", None)
    try:
        product = ProductInput.model_validate_json(raw)
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", "").strip()
        if not key or not model:
            st.error("Укажите OPENROUTER_API_KEY и OPENROUTER_MODEL в .env.")
        else:
            with st.spinner("Создаём карточку…"), httpx.Client() as client:
                card = generate_card(
                    product,
                    request=lambda p, issues: request_copy(
                        p, issues=issues, client=client, api_key=key, model=model
                    ),
                )
            # Keep the result and filename stable across Streamlit reruns and downloads.
            st.session_state["card"] = card
            st.session_state["card_input"] = raw
            st.session_state["export_basename"] = export_basename(product.name, datetime.now())
    except ValidationError:
        st.error("Некорректный JSON или неверные поля. Проверьте название и типы данных.")
    except GenerationError as exc:
        st.error(str(exc))
card = st.session_state.get("card")
if card:
    if st.session_state.get("card_input") != raw:
        st.warning("Входные данные изменились; показан результат предыдущей генерации.")
    st.subheader("Результат")
    if card.status == "needs_review":
        st.warning("Требуется уточнение или исправление данных.")
    st.caption(
        f"Заголовок: {len(card.seo_title.strip())}/70; "
        f"описание: {len(card.seo_description.strip())}/800–1200 символов"
    )
    markdown = render_markdown(card)
    st.markdown(markdown)
    basename = st.session_state["export_basename"]
    st.download_button("Скачать Markdown", markdown, f"{basename}.md", "text/markdown")
    st.download_button(
        "Скачать JSON", card.model_dump_json(indent=2), f"{basename}.json", "application/json"
    )
