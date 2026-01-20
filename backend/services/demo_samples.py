from typing import List, Dict


DEMO_UTTERANCE_SAMPLES: List[Dict[str, str]] = [
    {
        "speaker": "이민수",
        "text": "그런데 점심 뭐 먹을까요? 회사 앞에 새로 생긴 라멘집이 맛있다던데요.",
        "trigger": "TOPIC_DRIFT",
    },
    {
        "speaker": "김철수",
        "text": "이건 제가 결정했으니까, 다들 이대로 진행해 주세요.",
        "trigger": "PRINCIPLE_VIOLATION",
    },
    {
        "speaker": "김철수",
        "text": "이건 전적으로 개발팀 책임이에요. 왜 이렇게 기본도 안 돼 있죠?",
        "trigger": "PRINCIPLE_VIOLATION",
    },
    {
        "speaker": "이민수",
        "text": "A안이 낫긴 한데 리소스가 걱정돼요.",
        "trigger": "DECISION_STYLE",
    },
    {
        "speaker": "김철수",
        "text": "그럼 오늘 확정할 건 없는 건가요?",
        "trigger": "DECISION_STYLE",
    },
    {
        "speaker": "김철수",
        "text": "좋습니다. 그럼 다음 주까지 각자 태스크 정리해주세요.",
        "trigger": "PARTICIPATION_IMBALANCE",
    },
]
