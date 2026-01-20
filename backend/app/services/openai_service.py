from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.config import settings


class OpenAIService:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def is_available(self) -> bool:
        return self.client is not None

    def generate_recap(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.client:
            return None

        system_prompt = (
            "You are a meeting recap assistant. "
            "Return concise JSON with summary, decisions, action_items, and risks." 
            "Use short bullet phrases."
        )

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
        )

        raw_text = getattr(response, "output_text", "")
        if not raw_text:
            return None

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return None
