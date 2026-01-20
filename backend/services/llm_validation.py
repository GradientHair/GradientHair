"""Structured-output validation pipeline for LLM responses."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


@dataclass
class ValidationResult:
    ok: bool
    value: Optional[BaseModel] = None
    error: str = ""


class DSPyValidator:
    """Optional DSPy-based validation stage (disabled unless configured)."""

    def __init__(self) -> None:
        self.enabled = os.getenv("DSPY_VALIDATE") == "1"
        self._dspy = None
        if self.enabled:
            try:
                import dspy  # type: ignore
                self._dspy = dspy
            except Exception:
                self._dspy = None
                self.enabled = False

    def validate(self, payload: BaseModel) -> ValidationResult:
        if not self.enabled or self._dspy is None:
            return ValidationResult(ok=True, value=payload)

        try:
            dspy = self._dspy

            class ValidateJSON(dspy.Signature):
                """Validate that the output is consistent and safe."""

                input_json: str = dspy.InputField()
                is_valid: bool = dspy.OutputField()
                reason: str = dspy.OutputField()

            predictor = dspy.Predict(ValidateJSON)
            result = predictor(input_json=payload.model_dump_json())
            if not getattr(result, "is_valid", False):
                return ValidationResult(ok=False, error=str(getattr(result, "reason", "DSPy validation failed")))
        except Exception as exc:
            return ValidationResult(ok=False, error=f"DSPy validation error: {exc}")

        return ValidationResult(ok=True, value=payload)


class LLMStructuredOutputRunner:
    """1) Pydantic parse 2) error-feedback retry 3) optional DSPy validation."""

    def __init__(
        self,
        client: OpenAI,
        model: str,
        schema: type[T],
        max_retries: int = 2,
        custom_validator: Optional[Callable[[T], ValidationResult]] = None,
        use_dspy: bool = True,
    ) -> None:
        self.client = client
        self.model = model
        self.schema = schema
        self.max_retries = max_retries
        self.custom_validator = custom_validator
        self.dspy_validator = DSPyValidator() if use_dspy else None

    def run(self, prompt: str) -> Optional[T]:
        last_error: Optional[str] = None
        for _ in range(self.max_retries + 1):
            messages = [{"role": "user", "content": prompt}]
            if last_error:
                messages.append({
                    "role": "user",
                    "content": (
                        "이전 응답 처리 중 오류가 발생했습니다: "
                        f"{last_error}. 올바른 JSON만 다시 출력하세요."
                    ),
                })
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                parsed = self.schema.model_validate_json(response.choices[0].message.content)
                if self.custom_validator:
                    check = self.custom_validator(parsed)
                    if not check.ok:
                        last_error = check.error or "custom validation failed"
                        continue
                if self.dspy_validator:
                    dspy_result = self.dspy_validator.validate(parsed)
                    if not dspy_result.ok:
                        last_error = dspy_result.error
                        continue
                return parsed
            except ValidationError as exc:
                last_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
        return None
