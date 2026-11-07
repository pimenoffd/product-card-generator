import json

import httpx
import pytest

from product_cards.llm import GenerationError, request_copy
from product_cards.models import ProductInput


def test_request_uses_schema_and_returns_copy():
    def handler(request):
        body = json.loads(request.content)
        assert body["provider"]["require_parameters"] is True
        assert body["response_format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "seo_title": "Прибор",
                                    "seo_description": "Описание",
                                    "search_queries": ["запрос"],
                                    "commercial_block": "Назначение",
                                }
                            )
                        },
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = request_copy(
            ProductInput(name="Прибор"), issues=[], client=client, api_key="secret", model="test"
        )
    assert result.content.seo_title == "Прибор"


def test_auth_error_does_not_expose_secret():
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(401, text="secret"))
    ) as client:
        with pytest.raises(GenerationError) as exc:
            request_copy(
                ProductInput(name="Прибор"),
                issues=[],
                client=client,
                api_key="secret",
                model="test",
            )
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("status", [400, 401, 402, 403, 429, 500, 503])
def test_http_errors_are_safe(status):
    with httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(status, text="secret"))
    ) as client:
        with pytest.raises(GenerationError) as error:
            request_copy(
                ProductInput(name="Прибор"),
                issues=[],
                client=client,
                api_key="secret",
                model="test",
            )
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"error": {"message": "secret"}},
        {"choices": []},
        {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
        {"choices": [{"finish_reason": "stop", "message": {"refusal": "no", "content": "{}"}}]},
    ],
)
def test_invalid_api_response_is_reported(payload):
    with httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(GenerationError):
            request_copy(
                ProductInput(name="Прибор"),
                issues=[],
                client=client,
                api_key="secret",
                model="test",
            )


@pytest.mark.parametrize("exception", [httpx.ConnectError("failed"), httpx.ReadTimeout("timeout")])
def test_network_errors_are_reported(exception):
    def handler(request):
        raise exception

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GenerationError):
            request_copy(
                ProductInput(name="Прибор"),
                issues=[],
                client=client,
                api_key="secret",
                model="test",
            )


def test_json_array_response_is_reported():
    with httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[]))
    ) as client:
        with pytest.raises(GenerationError):
            request_copy(
                ProductInput(name="Прибор"),
                issues=[],
                client=client,
                api_key="secret",
                model="test",
            )


def test_provider_metadata_is_preserved():
    payload = {
        "model": "actual-provider-model",
        "usage": {"prompt_tokens": 7, "completion_tokens": 11, "total_tokens": 18},
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "seo_title": "Прибор",
                            "seo_description": "Текст",
                            "search_queries": ["Прибор"],
                            "commercial_block": "Назначение",
                        }
                    )
                },
            }
        ],
    }
    with httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    ) as client:
        response = request_copy(
            ProductInput(name="Прибор"),
            issues=[],
            client=client,
            api_key="test",
            model="requested-model",
        )
    assert response.model == "actual-provider-model"
    assert response.usage.prompt_tokens == 7
    assert response.usage.completion_tokens == 11
