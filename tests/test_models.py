import pytest
from pydantic import ValidationError

from product_cards.models import ProductInput


def test_input_preserves_specifications():
    item = ProductInput(name=" Манометр ", specs={"диапазон": "0–1,6 МПа"})
    assert item.name == "Манометр"
    assert item.specs == {"диапазон": "0–1,6 МПа"}
    assert item.manufacturer is None


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_rejected(name):
    with pytest.raises(ValidationError):
        ProductInput(name=name)


def test_invalid_specification_type_rejected():
    with pytest.raises(ValidationError):
        ProductInput(name="Прибор", specs={"диапазон": 123})


@pytest.mark.parametrize(
    "raw", ["{bad", "", "[]", '{"name": null}', '{"name": "  "}', '{"name": "x", "specs": []}']
)
def test_invalid_json_or_fields_rejected(raw):
    with pytest.raises(ValidationError):
        ProductInput.model_validate_json(raw)
