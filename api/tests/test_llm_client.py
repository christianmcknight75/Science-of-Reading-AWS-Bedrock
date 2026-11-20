from typing import Any

import pytest

from app.llm import BedrockLLM, LLMError
from app.prompt import ANSWER_TOOL


class FakeBedrock:
    def __init__(
        self, response: dict[str, Any] | None = None, error: Exception | None = None
    ) -> None:
        self.response = response or {}
        self.error = error
        self.request: dict[str, Any] = {}

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.request = kwargs
        if self.error:
            raise self.error
        return self.response


def call(client: FakeBedrock, **kw: Any) -> Any:
    llm = BedrockLLM(client, region="us-east-2", **kw)
    return llm.converse(model_id="m", system="s", user="u", max_tokens=50, tool=ANSWER_TOOL)


def test_request_forces_the_tool_caps_tokens_and_uses_temperature_zero() -> None:
    fake = FakeBedrock(
        {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "name": "submit_answer",
                                "input": {"answerable": False, "claims": []},
                            }
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 10, "outputTokens": 3},
        }
    )
    out = call(fake)
    assert fake.request["modelId"] == "m"
    assert fake.request["inferenceConfig"] == {"maxTokens": 50, "temperature": 0}
    assert fake.request["toolConfig"]["toolChoice"] == {"tool": {"name": "submit_answer"}}
    assert "guardrailConfig" not in fake.request
    assert out.tool_input == {"answerable": False, "claims": []} and out.input_tokens == 10


def test_guardrail_is_attached_when_configured() -> None:
    fake = FakeBedrock({"output": {"message": {"content": []}}})
    call(fake, guardrail_id="gr-1", guardrail_version="3")
    assert fake.request["guardrailConfig"] == {
        "guardrailIdentifier": "gr-1",
        "guardrailVersion": "3",
    }


def test_guardrail_intervention_and_sdk_errors_become_llm_error() -> None:
    with pytest.raises(LLMError):
        call(FakeBedrock({"stopReason": "guardrail_intervened"}))
    with pytest.raises(LLMError):
        call(FakeBedrock(error=RuntimeError("AccessDenied")))
