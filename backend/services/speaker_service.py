import asyncio
import json
from openai import OpenAI

from models.meeting import Participant


class SpeakerService:
    def __init__(self):
        self.client = OpenAI()
        self.participants: list[Participant] = []
        self.recent_context: list[dict] = []

    def set_participants(self, participants: list[Participant]):
        self.participants = participants

    async def identify_speaker(self, text: str) -> dict:
        if not self.participants:
            return {"speaker": "Unknown", "confidence": 0.0, "text_ko": text}

        participant_info = json.dumps(
            [{"name": p.name, "role": p.role} for p in self.participants],
            ensure_ascii=False,
        )

        context_str = json.dumps(self.recent_context[-5:], ensure_ascii=False)

        prompt = f"""참석자 목록과 최근 대화 컨텍스트를 기반으로 화자를 식별하세요.
모든 텍스트 출력은 반드시 한국어로만 작성하세요. 입력이 다른 언어면 자연스럽게 한국어로 번역하세요.
응답의 text_ko는 한글, 숫자, 공백, 기본 구두점만 사용하세요.

참석자:
{participant_info}

최근 대화:
{context_str}

새 발화:
"{text}"

JSON으로 응답:
{{"speaker": "화자 이름", "confidence": 0.0-1.0, "text_ko": "한국어 전사"}}
"""

        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        self.recent_context.append({"speaker": result["speaker"], "text": result.get("text_ko", text)})
        if len(self.recent_context) > 10:
            self.recent_context.pop(0)

        return result

    async def normalize_text(self, text: str) -> str:
        prompt = f"""다음 문장을 한국어로만 자연스럽게 변환하세요.
응답은 한글, 숫자, 공백, 기본 구두점만 사용하세요.

문장:
"{text}"

JSON으로 응답:
{{"text_ko": "한국어 문장"}}
"""
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("text_ko", text)
