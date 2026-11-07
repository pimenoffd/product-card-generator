from streamlit.testing.v1 import AppTest


def test_invalid_json_shows_error():
    app = AppTest.from_file("../app.py").run()
    app.text_area[0].set_value("{bad")
    app.button[0].click().run()
    assert any("Некорректный JSON" in error.value for error in app.error)


def test_missing_required_name_shows_error():
    app = AppTest.from_file("../app.py").run()
    app.text_area[0].set_value('{"name": "  "}')
    app.button[0].click().run()
    assert any("Некорректный JSON" in error.value for error in app.error)


def test_successful_generation_is_not_repeated_on_rerun(monkeypatch):
    from product_cards.models import GeneratedCopy, GenerationResponse

    calls = []

    def request(product, **kwargs):
        calls.append(product.name)
        return GenerationResponse(
            model="test",
            content=GeneratedCopy(
                seo_title="Прибор",
                seo_description="а" * 800,
                search_queries=["один", "два", "три"],
                commercial_block="Назначение",
            ),
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_MODEL", "test")
    monkeypatch.setattr("product_cards.llm.request_copy", request)
    app = AppTest.from_file("../app.py").run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["card"].metadata.models == ["test"]
    basename = app.session_state["export_basename"]
    app.run()
    assert len(calls) == 1
    assert app.session_state["export_basename"] == basename
