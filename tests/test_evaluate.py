from product_cards.evaluate import assess
from product_cards.models import ProductCard, ProductInput


def make_card(text):
    return ProductCard(
        seo_title="Прибор",
        seo_description=text,
        search_queries=["один", "два", "три"],
        commercial_block="Назначение",
        specs={"давление": "1,5 МПа"},
        missing_fields=[],
        warnings=[],
        status="valid",
    )


def test_evaluation_flags_new_numbers_and_service_text():
    product = ProductInput(name="Прибор", specs={"давление": "1,5 МПа"})
    report = assess(product, make_card("Данных недостаточно. Напряжение 220 В."))
    assert report["unsupported_numbers"] == ["220"]
    assert report["service_text_detected"] is True
    assert report["manual_review"] is None
    assert report["format_issues"]


def test_evaluation_accepts_decimal_separator_change():
    product = ProductInput(name="Прибор", specs={"давление": "1,5 МПа"})
    report = assess(product, make_card("Давление 1.5 МПа."))
    assert report["unsupported_numbers"] == []
    assert report["specs_preserved"] is True


def test_historical_service_wording_is_detected():
    card = make_card(
        "Отсутствие данных о сертификатах не позволяет расширить описание. "
        "Рекомендуется обратиться к производителю."
    )
    report = assess(ProductInput(name="Прибор"), card)
    assert report["service_text_detected"] is True


def test_live_progress_is_visible_before_request_and_reports_error(tmp_path, monkeypatch, capsys):
    import json
    import sys

    from product_cards import evaluate
    from product_cards.llm import GenerationError

    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{"id": "case-1", "input": {"name": "Прибор"}}]))
    output = tmp_path / "report.json"
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    monkeypatch.setattr(
        sys, "argv", ["evaluate", "--live", "--cases", str(cases), "--output", str(output)]
    )

    def fail_request(*args, **kwargs):
        progress = capsys.readouterr().out
        assert "1/1" in progress and "case-1" in progress
        raise GenerationError("request failed")

    monkeypatch.setattr(evaluate, "generate_card", fail_request)
    assert evaluate.main() == 1
    assert "request failed" in capsys.readouterr().out
    assert json.loads(output.read_text())["cases"][0]["error"] == "request failed"


def test_saved_benchmark_and_missing_results(tmp_path):
    import json
    import subprocess
    import sys

    output = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "product_cards.evaluate",
            "--cases",
            "demo/cases.json",
            "--results",
            "demo/results.json",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "[1/2] historical-manometer: processing" in result.stdout
    assert "[2/2] historical-laser: done" in result.stdout
    report = json.loads(output.read_text())
    assert len(report["cases"]) == 2
    assert all(case["assessment"]["specs_preserved"] for case in report["cases"])
    assert all(case["assessment"]["metadata"] for case in report["cases"])
    empty = tmp_path / "empty.json"
    empty.write_text("{}")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "product_cards.evaluate",
            "--cases",
            "demo/cases.json",
            "--results",
            str(empty),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert all("error" in case for case in json.loads(output.read_text())["cases"])
