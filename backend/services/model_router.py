"""Model selection based on task type and API constraints."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelChoice:
    model: str
    reason: str


class ModelRouter:
    """Route tasks to models with fallback when features are unsupported."""

    DEFAULT_MODEL = "gpt-5.2-chat-latest"
    FAST_MODEL = "gpt-5-mini"
    REASONING_MODEL = "gpt-5.2-pro"
    CODING_MODEL = "gpt-5.2-codex"

    @classmethod
    def select(
        cls,
        task: str,
        structured_output: bool = False,
        api: str = "chat",
    ) -> ModelChoice:
        if task == "fast":
            model = os.getenv("MODEL_FAST", cls.FAST_MODEL)
        elif task == "reasoning":
            model = os.getenv("MODEL_REASONING", cls.REASONING_MODEL)
        elif task == "coding":
            model = os.getenv("MODEL_CODING", cls.CODING_MODEL)
        else:
            model = os.getenv("MODEL_DEFAULT", cls.DEFAULT_MODEL)

        # Fallback for models that don't support structured outputs or API
        if structured_output and not cls._supports_structured_outputs(model):
            fallback = os.getenv("MODEL_FALLBACK_STRUCTURED", cls.DEFAULT_MODEL)
            return ModelChoice(
                model=fallback,
                reason=f"fallback: {model} lacks structured outputs",
            )

        if api != "responses" and cls._responses_only(model):
            fallback = os.getenv("MODEL_FALLBACK_API", cls.DEFAULT_MODEL)
            return ModelChoice(
                model=fallback,
                reason=f"fallback: {model} requires Responses API",
            )

        return ModelChoice(model=model, reason="selected")

    @staticmethod
    def _supports_structured_outputs(model: str) -> bool:
        # GPT-5.2 pro does not support structured outputs (Responses API doc).
        if model.startswith("gpt-5.2-pro"):
            return False
        return True

    @staticmethod
    def _responses_only(model: str) -> bool:
        # GPT-5.2 pro is documented as Responses-only.
        if model.startswith("gpt-5.2-pro"):
            return True
        return False
