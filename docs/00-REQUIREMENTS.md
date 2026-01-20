# MeetingMod - Requirements Specification

> Clarified requirements for OpenAI Multi-Agent Hackathon (2026.01.20)

## Original Requirement

"회의시 미팅이 잘 진행되게끔 도와주는 moderator agent - 회의가 진행될 때 주제에 벗어난 이야기를 하는 경우가 문제가 될 수 있음. 이 시점에 개입해서 회의를 올바른 방향으로 이끌어 나가야 함"

---

## Clarified Specification

### Goal
회의 중 실시간으로 모니터링하여 주제 이탈, 원칙 위반, 참여 불균형 시 적극적으로 개입하는 AI Meeting Moderator

### Scope

| Feature | Included | Notes |
|---------|----------|-------|
| 회의 준비 자료 입력 | Yes | 참석자, 아젠다, 회의 원칙 |
| 실시간 음성 인식 | Yes | Realtime STT, 실제 마이크 입력 |
| 화자 자동 분리 | Yes | 참석자 목록 기반 AI 분리 |
| Agent 실시간 개입 | Yes | 경고음 + 화면 Toast |
| 회의록 저장 | Yes | 회의별 디렉토리 + .md 파일 |
| 이메일 발송 | No | 해커톤 MVP 범위 외 |

### Technical Decisions

| Category | Decision | Rationale |
|----------|----------|-----------|
| **Backend** | Python 3.12 + OpenAI Agents SDK | 해커톤 주제 fit, Agent 구현 용이 |
| **Web Server** | FastAPI (필요시) | WebSocket 지원, 경량 |
| **Frontend** | Next.js + React + shadcn/ui | 빠른 UI 개발, 실시간 업데이트 |
| **Storage** | 회의별 디렉토리 + .md 파일 | 단순, 가독성, 버전 관리 가능 |
| **Audio Input** | 실제 마이크 → **OpenAI Realtime API** | 진정한 실시간 STT, 저지연 |
| **Intervention Output** | 경고음 + 화면 Toast | 시청각 피드백 |
| **Speaker Diarization** | AI 자동 분리 (GPT-5.2 기반) | 고정확도 화자 분리 |
| **Meeting Principles** | Agile + AWS LP (편집 가능) | 유연한 원칙 설정 |
| **Alert Sound** | 짧고 부드러운 차임벨 (1초 이내) | 주의 환기 but 방해 최소화 |

### Constraints

1. **개입 타이밍**: 발화자가 말을 멈췄을 때 (용기있게 개입!)
2. **회의 원칙**: 사전 정의된 페이지에서 편집 가능해야 함
3. **저장 구조**: `meetings/{meeting_id}/` 디렉토리 하위에 파일 저장
4. **Python 버전**: 3.12
5. **데모 환경**: localhost, 맥북 오디오 입력

### Success Criteria

- [ ] 주제 이탈 시 경고음과 함께 복귀 유도 메시지 출력
- [ ] 회의 원칙(Agile, AWS LP) 위반 시 구체적 지적
- [ ] 발언 통계 기반 참여 불균형 감지 및 독려
- [ ] 회의 종료 시 회의록 자동 생성 (Markdown)
- [ ] Action Item 추출 및 담당자 할당

---

## Open Questions (구현 시 결정)

### 1. 원칙 위반 감지 방식

| Option | Pros | Cons |
|--------|------|------|
| **LLM 직접 판단** | 컨텍스트 이해 높음 | 비용, 지연 |
| **Embedding 유사도** | 빠름, 비용 효율적 | 맥락 이해 제한 |
| **키워드 + 패턴** | 매우 빠름 | 유연성 낮음 |

**권장**: GPT-5.2 직접 판단 (해커톤에서는 정확도 우선)

### 2. 화자 분리 방식

| Option | Pros | Cons |
|--------|------|------|
| **GPT-5.2 기반 AI 분리** | 고정확도, 컨텍스트 이해 | API 비용 |
| **Whisper + pyannote** | 통합 파이프라인 | 설정 복잡 |
| **버튼 기반 수동** | 단순, 정확 | 사용자 부담 |

**권장**: GPT-5.2 기반 AI 자동 분리 (참석자 목록 + 발화 컨텍스트 활용)

---

## Storage Structure

```
meetings/
├── 2026-01-20-sprint-review/
│   ├── preparation.md       # 회의 준비 자료
│   ├── principles.md        # 적용된 회의 원칙
│   ├── transcript.md        # 실시간 녹취록
│   ├── interventions.md     # Agent 개입 기록
│   ├── summary.md           # 회의 요약
│   └── action-items.md      # Action Items
│
└── principles/              # 회의 원칙 템플릿
    ├── agile.md
    └── aws-leadership.md
```

---

## Meeting Principles Examples

### Agile 원칙 (principles/agile.md)
```markdown
# Agile Meeting Principles

1. **수평적 의사결정**: 모든 참석자의 의견을 동등하게 존중
2. **타임박스**: 정해진 시간 내 논의 완료
3. **Action-oriented**: 모든 논의는 Action Item으로 연결
4. **짧고 집중**: 불필요한 발언 최소화
5. **투명성**: 정보 공유에 숨김 없음
```

### AWS Leadership Principles (principles/aws-leadership.md)
```markdown
# AWS Leadership Principles for Meetings

1. **Customer Obsession**: 고객 관점에서 논의
2. **Ownership**: 책임감 있는 의견 제시
3. **Disagree and Commit**: 이견 표출 후 결정 따르기
4. **Have Backbone; Disagree**: 동의하지 않으면 정중히 반박
5. **Dive Deep**: 세부사항까지 파악
6. **Bias for Action**: 빠른 결정, 실행 우선
```

---

*Last updated: 2026-01-20*
