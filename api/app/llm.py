"""Claude on Bedrock through the Converse API. Model IDs are passed in by the caller (config)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LLMError(Exception):
    """The model call failed or was blocked. The engine turns this into an honest fallback."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class LLMResult:
    tool_input: dict[str, Any] | None
    text: str
    input_tokens: int
    output_tokens: int


class LLM(Protocol):
    def converse(
        self, *, model_id: str, system: str, user: str, max_tokens: int, tool: ToolSpec
    ) -> LLMResult: ...


class BedrockLLM:
    def __init__(
        self,
        client: Any = None,
        *,
        region: str,
        profile: str = "",
        guardrail_id: str = "",
        guardrail_version: str = "DRAFT",
    ) -> None:
        if client is None:
            import boto3

            session = boto3.Session(profile_name=profile or None, region_name=region)
            client = session.client("bedrock-runtime")
        self._client = client
        self._guardrail = (
            {"guardrailIdentifier": guardrail_id, "guardrailVersion": guardrail_version}
            if guardrail_id
            else None
        )

    def converse(
        self, *, model_id: str, system: str, user: str, max_tokens: int, tool: ToolSpec
    ) -> LLMResult:
        request: dict[str, Any] = {
            "modelId": model_id,
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0},
            "toolConfig": {
                "tools": [
                    {
                        "toolSpec": {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": {"json": tool.schema},
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": tool.name}},
            },
        }
        if self._guardrail:
            request["guardrailConfig"] = self._guardrail
        try:
            resp = self._client.converse(**request)
        except Exception as exc:  # noqa: BLE001 (any SDK or network failure becomes LLMError)
            raise LLMError(f"model call failed: {type(exc).__name__}") from exc
        if resp.get("stopReason") == "guardrail_intervened":
            raise LLMError("blocked by guardrail")
        tool_input: dict[str, Any] | None = None
        text = ""
        for block in resp.get("output", {}).get("message", {}).get("content", []):
            if "toolUse" in block and block["toolUse"].get("name") == tool.name:
                tool_input = block["toolUse"].get("input")
            elif "text" in block:
                text += block["text"]
        usage = resp.get("usage", {})
        return LLMResult(
            tool_input, text, int(usage.get("inputTokens", 0)), int(usage.get("outputTokens", 0))
        )
