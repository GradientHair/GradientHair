# MeetingMod - Multi-Agent Architecture Design

> OpenAI Agents SDK Handoff 패턴 기반 고수준 Multi-Agent 시스템 설계

---

## 1. 요구사항 요약

### 1.1 Original Requirement
"멀티에이전트 시스템을 구축하는 만큼 컨텍스트를 가지고 여러 에이전트가 서로 긴밀하게 영향을 끼쳐야 해. 오디오를 텍스트로 처리 → 텍스트 관찰 → 발화 구분 → Intent 파악 → 분기 처리 → 반복"

### 1.2 결정사항

| 항목 | 결정 |
|------|------|
| 컨텍스트 공유 | **Shared State Store** (중앙 상태 저장소) |
| 발화 구분 | **침묵 기반 (1.5초)** |
| Intent 분류 | **복합 (행위 + 원칙 + 감정)** |
| Agent 구조 | **Handoff 패턴** (Triage Agent → 전문 Agents) |
| Agent 범위 | **기능 도메인별** (Topic, Principle, Participation, Sentiment) |
| 분석 주기 | **발화 종료 시마다** |
| 병렬 호출 | **예**, 복수 전문 Agent 동시 분석 |
| State 범위 | **전체 회의 컨텍스트** |
| 개입 병합 | **복수 개입 허용** (하나의 메시지로 병합) |

---

## 2. 아키텍처 개요

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SHARED STATE STORE                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Transcript  │ │ Participants│ │  Principles │ │ Meeting Context         ││
│  │ Buffer      │ │ & Stats     │ │ & Agenda    │ │ (interventions, etc.)   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
         │                │                │                │
         └────────────────┴────────────────┴────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR AGENT                                   │
│                   (회의 상태 관리, 라이프사이클 제어)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
         ┌─────────────────┐           ┌─────────────────┐
         │   PREP AGENT    │           │  REVIEW AGENT   │
         │  (회의 전 준비)  │           │   (회의 후 정리) │
         └─────────────────┘           └─────────────────┘

                    ▼ (회의 진행 중)

┌─────────────────────────────────────────────────────────────────────────────┐
│                          TRIAGE AGENT                                        │
│              (발화 수신 → Intent 분류 → Handoff 결정)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┬──────────────┐
                    │              │              │              │
                    ▼              ▼              ▼              ▼
         ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
         │   TOPIC     │ │ PRINCIPLE   │ │PARTICIPATION│ │  SENTIMENT  │
         │   AGENT     │ │   AGENT     │ │   AGENT     │ │   AGENT     │
         │             │ │             │ │             │ │             │
         │ 주제 이탈    │ │ 원칙 위반    │ │ 발언 균형    │ │ 감정 톤     │
         │ 감지/처리   │ │ 감지/처리   │ │ 감지/처리   │ │ 감지/처리   │
         └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                    │              │              │              │
                    └──────────────┴──────────────┴──────────────┘
                                         │
                                         ▼
                              ┌─────────────────┐
                              │ INTERVENTION    │
                              │ MERGER          │
                              │ (개입 병합/출력) │
                              └─────────────────┘
```

### 2.2 처리 파이프라인

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Audio  │───▶│  STT    │───▶│ Speaker │───▶│ State   │───▶│ Triage  │
│ Capture │    │(Whisper)│    │  ID     │    │ Update  │    │ Agent   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                                  │
                                                 1.5초 침묵 감지 시
                                                                  │
                    ┌─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PARALLEL ANALYSIS (asyncio.gather)                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │TopicAgent   │ │PrincipleAgt │ │Participation│ │SentimentAgt │           │
│  │.analyze()   │ │.analyze()   │ │Agt.analyze()│ │.analyze()   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
         ┌─────────────────┐
         │ Intervention    │
         │ Merger          │───▶ 경고음 + Toast 출력
         │ (복수→단일 병합) │
         └─────────────────┘
```

---

## 3. Shared State Store 설계

### 3.1 State 구조

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class MeetingStatus(Enum):
    PREPARING = "preparing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@dataclass
class Utterance:
    """단일 발화 단위"""
    id: str
    timestamp: datetime
    speaker: str
    text: str
    duration: float
    confidence: float  # 화자 분리 신뢰도

@dataclass
class SpeakerStats:
    """참석자별 발언 통계"""
    name: str
    role: str
    utterance_count: int = 0
    total_duration: float = 0.0
    total_chars: int = 0
    last_spoke_at: Optional[datetime] = None

@dataclass
class Intervention:
    """Agent 개입 기록"""
    id: str
    timestamp: datetime
    agent_source: str  # 어떤 Agent가 발생시켰는지
    intervention_type: str
    message: str
    severity: str  # low, medium, high
    metadata: dict = field(default_factory=dict)
    acknowledged: bool = False

@dataclass
class MeetingState:
    """전체 회의 상태 - Shared State Store의 핵심"""

    # 기본 정보
    meeting_id: str
    title: str
    status: MeetingStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # 회의 설정
    agenda: list[str] = field(default_factory=list)
    principles: list[dict] = field(default_factory=list)
    participants: list[SpeakerStats] = field(default_factory=list)

    # 실시간 데이터
    transcript: list[Utterance] = field(default_factory=list)
    current_topic: Optional[str] = None
    parking_lot: list[str] = field(default_factory=list)

    # 개입 기록
    interventions: list[Intervention] = field(default_factory=list)
    pending_interventions: list[Intervention] = field(default_factory=list)

    # 분석 메타데이터
    last_analysis_at: Optional[datetime] = None
    analysis_count: int = 0
```

### 3.2 State Store 인터페이스

```python
from abc import ABC, abstractmethod
import asyncio

class StateStore(ABC):
    """State Store 추상 인터페이스"""

    @abstractmethod
    async def get_state(self, meeting_id: str) -> MeetingState:
        pass

    @abstractmethod
    async def update_state(self, meeting_id: str, updates: dict) -> MeetingState:
        pass

    @abstractmethod
    async def add_utterance(self, meeting_id: str, utterance: Utterance) -> None:
        pass

    @abstractmethod
    async def add_intervention(self, meeting_id: str, intervention: Intervention) -> None:
        pass

    @abstractmethod
    async def get_recent_utterances(self, meeting_id: str, count: int = 10) -> list[Utterance]:
        pass


class InMemoryStateStore(StateStore):
    """인메모리 구현 (해커톤용)"""

    def __init__(self):
        self._states: dict[str, MeetingState] = {}
        self._lock = asyncio.Lock()

    async def get_state(self, meeting_id: str) -> MeetingState:
        async with self._lock:
            return self._states.get(meeting_id)

    async def update_state(self, meeting_id: str, updates: dict) -> MeetingState:
        async with self._lock:
            state = self._states.get(meeting_id)
            if state:
                for key, value in updates.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
            return state

    async def add_utterance(self, meeting_id: str, utterance: Utterance) -> None:
        async with self._lock:
            state = self._states.get(meeting_id)
            if state:
                state.transcript.append(utterance)
                # 화자 통계 업데이트
                self._update_speaker_stats(state, utterance)

    async def add_intervention(self, meeting_id: str, intervention: Intervention) -> None:
        async with self._lock:
            state = self._states.get(meeting_id)
            if state:
                state.interventions.append(intervention)

    async def get_recent_utterances(self, meeting_id: str, count: int = 10) -> list[Utterance]:
        async with self._lock:
            state = self._states.get(meeting_id)
            if state:
                return state.transcript[-count:]
            return []

    def _update_speaker_stats(self, state: MeetingState, utterance: Utterance):
        for speaker in state.participants:
            if speaker.name == utterance.speaker:
                speaker.utterance_count += 1
                speaker.total_duration += utterance.duration
                speaker.total_chars += len(utterance.text)
                speaker.last_spoke_at = utterance.timestamp
                break
```

---

## 4. Agent 상세 설계

### 4.1 Triage Agent (Intent 분류 및 Handoff)

```python
from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# 전문 Agent들 (아래에서 정의)
topic_agent = TopicAgent()
principle_agent = PrincipleAgent()
participation_agent = ParticipationAgent()
sentiment_agent = SentimentAgent()

triage_agent = Agent(
    name="TriageAgent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are the Triage Agent for a meeting moderation system.

Your role:
1. Receive each utterance when the speaker stops talking (1.5s silence)
2. Analyze the utterance for multiple intent types simultaneously
3. Handoff to appropriate specialist agents for parallel analysis

Intent Categories to detect:
- TOPIC: Is this on-topic or off-topic? (→ TopicAgent)
- PRINCIPLE: Does this violate any meeting principles? (→ PrincipleAgent)
- PARTICIPATION: Is there participation imbalance? (→ ParticipationAgent)
- SENTIMENT: What is the emotional tone? (→ SentimentAgent)

IMPORTANT:
- Always call ALL specialist agents in parallel for comprehensive analysis
- Each agent will return whether intervention is needed
- You coordinate the results for the InterventionMerger
""",
    handoffs=[
        handoff(topic_agent, tool_name_override="analyze_topic"),
        handoff(principle_agent, tool_name_override="analyze_principle"),
        handoff(participation_agent, tool_name_override="analyze_participation"),
        handoff(sentiment_agent, tool_name_override="analyze_sentiment"),
    ],
    model="gpt-5.2"
)
```

### 4.2 Topic Agent (주제 이탈 감지)

```python
from pydantic import BaseModel

class TopicAnalysisInput(BaseModel):
    utterance: str
    current_topic: str
    agenda: list[str]
    recent_context: list[dict]

class TopicAnalysisResult(BaseModel):
    is_off_topic: bool
    confidence: float
    detected_topic: str
    suggested_parking_lot: str | None
    intervention_message: str | None

topic_agent = Agent(
    name="TopicAgent",
    instructions="""You are the Topic Analysis Agent.

Your role:
1. Analyze if the utterance is relevant to the current topic and agenda
2. Detect topic drift or tangential discussions
3. Suggest parking lot items for off-topic but valuable points

Analysis criteria:
- Direct relevance to agenda items
- Logical flow from previous discussion
- Business value vs social chatter

Output format:
- is_off_topic: true if discussion strayed from agenda
- confidence: 0.0-1.0 certainty level
- detected_topic: what the utterance is actually about
- suggested_parking_lot: if off-topic, what to save for later
- intervention_message: Korean message if intervention needed

Intervention tone: DIRECT and COURAGEOUS. Don't soften the message.
Example: "잠깐요, 아젠다에서 벗어났어요. '점심 메뉴'는 Parking Lot에 추가하고, 스프린트 계획으로 돌아갈게요."
""",
    model="gpt-5.2",
    output_type=TopicAnalysisResult
)
```

### 4.3 Principle Agent (원칙 위반 감지)

```python
class PrincipleAnalysisInput(BaseModel):
    utterance: str
    speaker: str
    principles: list[dict]
    recent_context: list[dict]

class PrincipleAnalysisResult(BaseModel):
    has_violation: bool
    violated_principles: list[str]
    violation_type: str | None  # "decision_style", "respect", "commitment", etc.
    severity: str  # "low", "medium", "high"
    intervention_message: str | None

principle_agent = Agent(
    name="PrincipleAgent",
    instructions="""You are the Principle Compliance Agent.

Your role:
1. Check utterances against configured meeting principles
2. Detect violations of Agile principles or AWS Leadership Principles
3. Generate constructive intervention messages

Common principle violations to detect:
- Top-down decision making (vs. collaborative)
- Dismissing others' opinions
- Making commitments without team agreement
- Lack of ownership ("not my job")
- Avoiding conflict when disagreement is healthy

Analysis approach:
- Consider cultural context (Korean business culture)
- Distinguish between authority-appropriate and principle-violating behavior
- Focus on behavior patterns, not single words

Intervention tone: DIRECT and COURAGEOUS. Call out violations clearly.
Example: "멈춰주세요! 'Disagree and Commit' 원칙 위반입니다. 결정 전에 이견 표현해야 해요. 다른 의견 있으신 분?"
""",
    model="gpt-5.2",
    output_type=PrincipleAnalysisResult
)
```

### 4.4 Participation Agent (발언 균형 감지)

```python
class ParticipationAnalysisInput(BaseModel):
    speaker_stats: list[dict]
    meeting_duration_minutes: float
    recent_speakers: list[str]
    participants: list[dict]

class ParticipationAnalysisResult(BaseModel):
    has_imbalance: bool
    dominant_speaker: str | None
    silent_participants: list[str]
    imbalance_ratio: float  # 0.0 = balanced, 1.0 = completely dominated
    intervention_message: str | None
    suggested_speaker: str | None

participation_agent = Agent(
    name="ParticipationAgent",
    instructions="""You are the Participation Balance Agent.

Your role:
1. Monitor speaking time distribution across participants
2. Identify dominant speakers and silent participants
3. Encourage balanced participation

Analysis thresholds:
- Alert when one person has >50% of speaking time (after 10+ minutes)
- Alert when someone hasn't spoken for 5+ minutes
- Consider role context (PM may legitimately speak more during planning)

Intervention strategy:
- Gently redirect from dominant speakers
- Actively invite silent participants
- Frame as seeking diverse perspectives, not criticism

Intervention tone: DIRECT and COURAGEOUS. Point out the imbalance.
Example: "잠깐요! 박영희 님 아직 한 번도 발언 안 하셨어요. 이 부분 어떻게 보세요?"
""",
    model="gpt-5.2",
    output_type=ParticipationAnalysisResult
)
```

### 4.5 Sentiment Agent (감정 톤 분석)

```python
class SentimentAnalysisInput(BaseModel):
    utterance: str
    speaker: str
    recent_context: list[dict]

class SentimentAnalysisResult(BaseModel):
    sentiment: str  # "positive", "neutral", "negative", "frustrated", "defensive"
    intensity: float  # 0.0-1.0
    concerning_pattern: bool
    intervention_needed: bool
    intervention_message: str | None

sentiment_agent = Agent(
    name="SentimentAgent",
    instructions="""You are the Sentiment Analysis Agent.

Your role:
1. Analyze emotional tone of utterances
2. Detect concerning patterns (frustration building, defensiveness, aggression)
3. Suggest interventions when emotional climate needs attention

Sentiment categories:
- positive: enthusiasm, agreement, constructive
- neutral: factual, informational
- negative: disagreement, concern, criticism
- frustrated: repeated concerns, sighing phrases
- defensive: justification, blame deflection

Intervention triggers:
- Rising frustration (multiple negative utterances from same person)
- Defensive patterns after criticism
- Aggressive tone toward specific individuals

Intervention tone: De-escalating but DIRECT.
Example: "잠깐 멈춰요. 감정이 고조되고 있어요. 각자 핵심 우려사항 한 가지씩만 말씀해 주세요."
""",
    model="gpt-5.2",
    output_type=SentimentAnalysisResult
)
```

---

## 5. Intervention Merger

### 5.1 병합 로직

```python
from dataclasses import dataclass

@dataclass
class MergedIntervention:
    """병합된 최종 개입"""
    types: list[str]
    message: str
    severity: str
    metadata: dict

class InterventionMerger:
    """복수 Agent의 개입 결과를 병합"""

    PRIORITY_ORDER = ["PRINCIPLE", "TOPIC", "PARTICIPATION", "SENTIMENT"]

    async def merge(
        self,
        topic_result: TopicAnalysisResult | None,
        principle_result: PrincipleAnalysisResult | None,
        participation_result: ParticipationAnalysisResult | None,
        sentiment_result: SentimentAnalysisResult | None
    ) -> MergedIntervention | None:
        """
        여러 Agent의 분석 결과를 하나의 개입으로 병합
        """
        interventions = []

        # 각 Agent 결과 수집
        if principle_result and principle_result.has_violation:
            interventions.append({
                "type": "PRINCIPLE",
                "message": principle_result.intervention_message,
                "severity": principle_result.severity,
                "priority": 1
            })

        if topic_result and topic_result.is_off_topic:
            interventions.append({
                "type": "TOPIC",
                "message": topic_result.intervention_message,
                "severity": "medium",
                "priority": 2
            })

        if participation_result and participation_result.has_imbalance:
            interventions.append({
                "type": "PARTICIPATION",
                "message": participation_result.intervention_message,
                "severity": "low",
                "priority": 3
            })

        if sentiment_result and sentiment_result.intervention_needed:
            interventions.append({
                "type": "SENTIMENT",
                "message": sentiment_result.intervention_message,
                "severity": "medium" if sentiment_result.intensity > 0.7 else "low",
                "priority": 4
            })

        if not interventions:
            return None

        # 복수 개입 병합
        return self._create_merged_intervention(interventions)

    def _create_merged_intervention(
        self,
        interventions: list[dict]
    ) -> MergedIntervention:
        """
        복수 개입을 하나의 자연스러운 메시지로 병합
        """
        # 우선순위순 정렬
        sorted_interventions = sorted(interventions, key=lambda x: x["priority"])

        types = [i["type"] for i in sorted_interventions]
        messages = [i["message"] for i in sorted_interventions if i["message"]]

        # 최고 심각도 선택
        severity_order = {"high": 3, "medium": 2, "low": 1}
        max_severity = max(interventions, key=lambda x: severity_order.get(x["severity"], 0))["severity"]

        # 메시지 병합 (LLM으로 자연스럽게 병합하거나, 가장 중요한 것만 사용)
        if len(messages) == 1:
            merged_message = messages[0]
        else:
            # 복수 메시지를 자연스럽게 연결
            merged_message = self._combine_messages(messages, types)

        return MergedIntervention(
            types=types,
            message=merged_message,
            severity=max_severity,
            metadata={"individual_interventions": interventions}
        )

    def _combine_messages(self, messages: list[str], types: list[str]) -> str:
        """복수 메시지를 하나로 자연스럽게 연결"""
        if len(messages) == 2:
            return f"{messages[0]} 그리고 {messages[1]}"
        else:
            # 가장 우선순위 높은 것만 사용
            return messages[0]
```

---

## 6. 전체 실행 흐름

### 6.1 Main Processing Loop

```python
import asyncio
from agents import Runner

class MeetingModerator:
    """메인 모더레이터 - 전체 흐름 조율"""

    def __init__(self, state_store: StateStore):
        self.state_store = state_store
        self.triage_agent = triage_agent
        self.intervention_merger = InterventionMerger()
        self.runner = Runner()

    async def on_utterance_complete(
        self,
        meeting_id: str,
        utterance: Utterance
    ):
        """
        발화 종료 시 호출 (1.5초 침묵 감지 후)
        """
        # 1. State에 발화 추가
        await self.state_store.add_utterance(meeting_id, utterance)

        # 2. 분석을 위한 컨텍스트 준비
        state = await self.state_store.get_state(meeting_id)
        recent_utterances = await self.state_store.get_recent_utterances(meeting_id, 10)

        # 3. 병렬로 모든 전문 Agent 분석 실행
        results = await asyncio.gather(
            self._analyze_topic(state, utterance, recent_utterances),
            self._analyze_principle(state, utterance, recent_utterances),
            self._analyze_participation(state),
            self._analyze_sentiment(utterance, recent_utterances),
            return_exceptions=True
        )

        topic_result, principle_result, participation_result, sentiment_result = results

        # 4. 결과 병합
        merged = await self.intervention_merger.merge(
            topic_result if not isinstance(topic_result, Exception) else None,
            principle_result if not isinstance(principle_result, Exception) else None,
            participation_result if not isinstance(participation_result, Exception) else None,
            sentiment_result if not isinstance(sentiment_result, Exception) else None
        )

        # 5. 개입 필요 시 출력
        if merged:
            intervention = Intervention(
                id=f"int_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.utcnow(),
                agent_source=",".join(merged.types),
                intervention_type=merged.types[0],  # 주요 타입
                message=merged.message,
                severity=merged.severity,
                metadata=merged.metadata
            )
            await self.state_store.add_intervention(meeting_id, intervention)

            # WebSocket으로 클라이언트에 전송
            await self._send_intervention(meeting_id, intervention)

    async def _analyze_topic(self, state, utterance, recent) -> TopicAnalysisResult:
        """TopicAgent 호출"""
        input_data = TopicAnalysisInput(
            utterance=utterance.text,
            current_topic=state.current_topic or state.agenda[0] if state.agenda else "",
            agenda=state.agenda,
            recent_context=[{"speaker": u.speaker, "text": u.text} for u in recent]
        )
        result = await self.runner.run(topic_agent, input=input_data.model_dump_json())
        return result.final_output

    # ... 다른 analyze 메서드들도 유사하게 구현
```

### 6.2 시퀀스 다이어그램

```
User        Frontend        Backend         TriageAgent     Specialists     Merger
 │              │              │                │               │            │
 │  말하기       │              │                │               │            │
 │─────────────▶│              │                │               │            │
 │              │   오디오     │                │               │            │
 │              │─────────────▶│                │               │            │
 │              │              │                │               │            │
 │  1.5초 침묵   │              │                │               │            │
 │              │   침묵감지   │                │               │            │
 │              │─────────────▶│                │               │            │
 │              │              │                │               │            │
 │              │              │  utterance     │               │            │
 │              │              │───────────────▶│               │            │
 │              │              │                │               │            │
 │              │              │                │  parallel     │            │
 │              │              │                │──────────────▶│            │
 │              │              │                │               │            │
 │              │              │                │   results     │            │
 │              │              │                │◀──────────────│            │
 │              │              │                │               │            │
 │              │              │                │      merge    │            │
 │              │              │                │───────────────┼───────────▶│
 │              │              │                │               │            │
 │              │              │  intervention  │               │            │
 │              │              │◀───────────────┼───────────────┼────────────│
 │              │              │                │               │            │
 │              │ 경고음+Toast │                │               │            │
 │              │◀─────────────│                │               │            │
 │              │              │                │               │            │
```

---

## 7. 구현 체크리스트

### Phase 1: 기반 구조
- [ ] Shared State Store 구현 (InMemoryStateStore)
- [ ] MeetingState 데이터 모델 정의
- [ ] State 접근 인터페이스 구현

### Phase 2: Agent 정의
- [ ] TriageAgent 구현 (Handoff 설정)
- [ ] TopicAgent 구현
- [ ] PrincipleAgent 구현
- [ ] ParticipationAgent 구현
- [ ] SentimentAgent 구현

### Phase 3: 통합
- [ ] InterventionMerger 구현
- [ ] MeetingModerator 메인 루프 구현
- [ ] 병렬 분석 실행 (asyncio.gather)
- [ ] WebSocket 연동

### Phase 4: 테스트
- [ ] 단위 테스트 (각 Agent)
- [ ] 통합 테스트 (전체 파이프라인)
- [ ] 데모 시나리오 검증

---

## 8. 참고: OpenAI Agents SDK 패턴

### Handoff Best Practice (SDK 문서 기반)

```python
from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# 1. 권장 프롬프트 접두사 사용
agent = Agent(
    name="MyAgent",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\n[실제 지시사항]"
)

# 2. Handoff 데이터 전달
from pydantic import BaseModel

class HandoffData(BaseModel):
    reason: str
    context: dict

async def on_handoff(ctx, input_data: HandoffData):
    print(f"Handoff 발생: {input_data.reason}")

specialized_agent = Agent(name="Specialist")

main_agent = Agent(
    name="Main",
    handoffs=[
        handoff(
            specialized_agent,
            on_handoff=on_handoff,
            input_type=HandoffData
        )
    ]
)

# 3. 병렬 실행 (코드 기반 오케스트레이션)
import asyncio

async def parallel_analysis(utterance: str):
    results = await asyncio.gather(
        runner.run(topic_agent, input=utterance),
        runner.run(principle_agent, input=utterance),
        runner.run(participation_agent, input=utterance),
        runner.run(sentiment_agent, input=utterance)
    )
    return results
```
