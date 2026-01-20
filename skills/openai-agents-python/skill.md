# OpenAI Agents Python SDK - Multi-Agent Development Guide

## Overview

이 스킬은 OpenAI Agents Python SDK를 사용하여 multi-agent 시스템을 개발할 때 참고할 best practices를 제공합니다.

**공식 문서**: https://openai.github.io/openai-agents-python/

## Installation

```bash
pip install openai-agents
```

환경 변수 설정:
```bash
export OPENAI_API_KEY="your-api-key"
```

---

## Core Concepts

### 1. Agent

Agent는 LLM, instructions, tools로 구성된 핵심 단위입니다.

```python
from agents import Agent, Runner

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant",
    model="gpt-4o",  # 또는 "gpt-4o-mini"
    tools=[],        # 사용할 도구들
    handoffs=[],     # 위임할 에이전트들
)
```

**주요 속성**:
- `name`: 에이전트 식별자 (필수)
- `instructions`: 시스템 프롬프트 (문자열 또는 함수)
- `model`: 사용할 LLM 모델
- `tools`: 에이전트가 사용할 도구 목록
- `handoffs`: 위임 가능한 에이전트 목록
- `output_type`: 구조화된 출력 타입 (Pydantic 모델)
- `model_settings`: temperature, top_p 등 모델 설정

### 2. Tools

#### Function Tools (가장 일반적)

```python
from agents import function_tool

@function_tool
def get_weather(city: str) -> str:
    """지정된 도시의 날씨를 조회합니다.

    Args:
        city: 조회할 도시명
    """
    return f"The weather in {city} is sunny"

@function_tool
async def fetch_data(url: str, timeout: int = 30) -> str:
    """URL에서 데이터를 가져옵니다."""
    # 비동기 함수도 지원
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=timeout) as response:
            return await response.text()
```

**Best Practice**:
- 함수명은 명확하게 (도구 이름으로 사용됨)
- docstring 필수 (도구 설명으로 사용됨)
- 타입 힌트 필수 (JSON 스키마 자동 생성)
- Args 섹션에 파라미터 설명 포함

#### Hosted Tools (OpenAI 제공)

```python
from agents import Agent
from agents.tools import WebSearchTool, FileSearchTool, CodeInterpreterTool

agent = Agent(
    name="Research Agent",
    tools=[
        WebSearchTool(),
        FileSearchTool(vector_store_ids=["vs_xxx"]),
        CodeInterpreterTool(),
    ]
)
```

### 3. Handoffs

에이전트 간 작업 위임 메커니즘입니다.

```python
from agents import Agent, handoff

billing_agent = Agent(name="Billing Agent", instructions="Handle billing...")
support_agent = Agent(name="Support Agent", instructions="Handle support...")

triage_agent = Agent(
    name="Triage Agent",
    instructions="""You are a triage agent.
    - For billing questions, hand off to Billing Agent
    - For support questions, hand off to Support Agent
    """,
    handoffs=[billing_agent, support_agent]
)
```

**커스텀 Handoff**:
```python
from agents import handoff
from pydantic import BaseModel

class EscalationData(BaseModel):
    reason: str
    priority: str

async def on_handoff(ctx, data: EscalationData):
    print(f"Escalating: {data.reason} (Priority: {data.priority})")

escalation_handoff = handoff(
    agent=escalation_agent,
    input_type=EscalationData,
    on_handoff=on_handoff,
    tool_name_override="escalate_to_human"
)
```

### 4. Context (의존성 주입)

```python
from dataclasses import dataclass
from agents import Agent, RunContextWrapper

@dataclass
class AppContext:
    user_id: str
    is_premium: bool
    db_connection: Any

def dynamic_instructions(ctx: RunContextWrapper[AppContext], agent: Agent) -> str:
    user_type = "premium" if ctx.context.is_premium else "free"
    return f"You are helping a {user_type} user. User ID: {ctx.context.user_id}"

agent = Agent[AppContext](
    name="Context-Aware Agent",
    instructions=dynamic_instructions,
)

# 실행 시 context 전달
result = await Runner.run(
    agent,
    "Hello",
    context=AppContext(user_id="123", is_premium=True, db_connection=db)
)
```

### 5. Output Types (구조화된 출력)

```python
from pydantic import BaseModel
from agents import Agent

class TaskPlan(BaseModel):
    title: str
    steps: list[str]
    estimated_time: str

planner_agent = Agent(
    name="Planner",
    instructions="Create detailed task plans",
    output_type=TaskPlan
)

result = await Runner.run(planner_agent, "Plan a website redesign")
plan: TaskPlan = result.final_output  # 타입 안전한 접근
```

### 6. Guardrails

입력/출력 검증 메커니즘입니다.

```python
from agents import Agent, input_guardrail, output_guardrail, GuardrailFunctionOutput

@input_guardrail
async def content_filter(ctx, agent, input) -> GuardrailFunctionOutput:
    # 입력 검증 로직
    is_inappropriate = check_content(input)
    return GuardrailFunctionOutput(
        output_info={"checked": True},
        tripwire_triggered=is_inappropriate
    )

@output_guardrail
async def output_validator(ctx, agent, output) -> GuardrailFunctionOutput:
    # 출력 검증 로직
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=False
    )

agent = Agent(
    name="Safe Agent",
    input_guardrails=[content_filter],
    output_guardrails=[output_validator]
)
```

---

## Running Agents

### 기본 실행

```python
from agents import Agent, Runner

# 동기 실행
result = Runner.run_sync(agent, "Hello")
print(result.final_output)

# 비동기 실행
result = await Runner.run(agent, "Hello")
print(result.final_output)

# 스트리밍 실행
async with Runner.run_streamed(agent, "Hello") as stream:
    async for event in stream.stream_events():
        if event.type == "raw_response_event":
            print(event.data, end="", flush=True)
```

### RunConfig 설정

```python
from agents import RunConfig

config = RunConfig(
    model="gpt-4o",
    max_turns=10,
    tracing_disabled=False,
    trace_include_sensitive_data=False,
)

result = await Runner.run(agent, "Hello", run_config=config)
```

### 대화 이력 관리

```python
# 수동 관리
result1 = await Runner.run(agent, "My name is Alice")
result2 = await Runner.run(
    agent,
    result1.to_input_list() + [{"role": "user", "content": "What's my name?"}]
)

# 자동 관리 (Sessions)
from agents.sessions import SQLiteSession

session = SQLiteSession("./conversations.db")
result = await Runner.run(agent, "Hello", session=session)
```

---

## Multi-Agent Patterns

### Pattern 1: Manager (Agents as Tools)

중앙 관리 에이전트가 하위 에이전트를 도구로 호출합니다.

```python
researcher = Agent(name="Researcher", instructions="Research topics thoroughly")
writer = Agent(name="Writer", instructions="Write clear, engaging content")
reviewer = Agent(name="Reviewer", instructions="Review and improve content")

manager = Agent(
    name="Content Manager",
    instructions="""You manage content creation.
    Use the researcher for gathering information.
    Use the writer for creating drafts.
    Use the reviewer for quality checks.
    """,
    tools=[
        researcher.as_tool(
            tool_name="research",
            tool_description="Research a topic and gather information"
        ),
        writer.as_tool(
            tool_name="write_content",
            tool_description="Write content based on research"
        ),
        reviewer.as_tool(
            tool_name="review_content",
            tool_description="Review and suggest improvements"
        ),
    ]
)
```

### Pattern 2: Handoffs (Sequential Delegation)

작업을 전문 에이전트에게 순차적으로 위임합니다.

```python
intake_agent = Agent(
    name="Intake",
    instructions="Gather initial information and route to appropriate specialist",
    handoffs=[technical_agent, billing_agent, general_agent]
)

# 실행하면 자동으로 적절한 에이전트로 handoff
result = await Runner.run(intake_agent, user_query)
```

### Pattern 3: Parallel Execution

독립적인 작업을 병렬로 실행합니다.

```python
import asyncio

async def parallel_analysis(data: str):
    sentiment_agent = Agent(name="Sentiment", instructions="Analyze sentiment")
    summary_agent = Agent(name="Summary", instructions="Create a summary")
    keywords_agent = Agent(name="Keywords", instructions="Extract keywords")

    results = await asyncio.gather(
        Runner.run(sentiment_agent, data),
        Runner.run(summary_agent, data),
        Runner.run(keywords_agent, data),
    )

    return {
        "sentiment": results[0].final_output,
        "summary": results[1].final_output,
        "keywords": results[2].final_output,
    }
```

### Pattern 4: Pipeline (Chained Agents)

에이전트 출력을 다음 에이전트 입력으로 연결합니다.

```python
async def content_pipeline(topic: str):
    # Step 1: Research
    research_result = await Runner.run(researcher, f"Research: {topic}")

    # Step 2: Write draft
    draft_result = await Runner.run(
        writer,
        f"Write about: {topic}\n\nResearch:\n{research_result.final_output}"
    )

    # Step 3: Review and improve
    final_result = await Runner.run(
        reviewer,
        f"Review and improve:\n{draft_result.final_output}"
    )

    return final_result.final_output
```

### Pattern 5: Feedback Loop

품질 기준을 충족할 때까지 반복합니다.

```python
async def iterative_improvement(content: str, max_iterations: int = 3):
    evaluator = Agent(
        name="Evaluator",
        output_type=EvaluationResult  # score: float, feedback: str, is_good: bool
    )
    improver = Agent(name="Improver", instructions="Improve based on feedback")

    current_content = content
    for i in range(max_iterations):
        eval_result = await Runner.run(evaluator, current_content)

        if eval_result.final_output.is_good:
            break

        improve_result = await Runner.run(
            improver,
            f"Content:\n{current_content}\n\nFeedback:\n{eval_result.final_output.feedback}"
        )
        current_content = improve_result.final_output

    return current_content
```

---

## Tracing

```python
from agents import trace, custom_span

# 전체 워크플로우 추적
with trace("My Workflow", group_id="session_123"):
    result = await Runner.run(agent, "Hello")

    # 커스텀 span 추가
    with custom_span("Post-processing"):
        processed = process_result(result)
```

**비활성화**:
```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

---

## Error Handling

```python
from agents import (
    MaxTurnsExceeded,
    ModelBehaviorError,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
)

try:
    result = await Runner.run(agent, user_input, run_config=RunConfig(max_turns=5))
except MaxTurnsExceeded:
    print("Agent exceeded maximum turns")
except InputGuardrailTripwireTriggered as e:
    print(f"Input blocked: {e.guardrail_result}")
except OutputGuardrailTripwireTriggered as e:
    print(f"Output blocked: {e.guardrail_result}")
except ModelBehaviorError as e:
    print(f"Model error: {e}")
```

---

## Best Practices

### 1. Agent Design
- **단일 책임**: 각 에이전트는 하나의 명확한 역할만 수행
- **명확한 instructions**: 구체적이고 상세한 지시사항 작성
- **적절한 도구 선택**: 필요한 도구만 제공 (너무 많으면 혼란)

### 2. Tool Design
- **명확한 이름**: 도구의 기능을 명확히 설명하는 이름
- **상세한 docstring**: LLM이 도구 사용법을 이해할 수 있도록
- **타입 힌트 필수**: 자동 스키마 생성에 필요
- **에러 처리**: 실패 시 명확한 에러 메시지 반환

### 3. Multi-Agent Orchestration
- **단순하게 시작**: 복잡한 패턴보다 단순한 구조로 시작
- **Handoffs vs Tools**:
  - Handoffs: 대화 컨텍스트 전체 전달, 완전한 제어권 이전
  - Tools: 특정 작업만 위임, 원래 에이전트가 제어 유지
- **적절한 granularity**: 너무 세분화하지 않기

### 4. Performance
- **병렬 실행**: 독립적인 작업은 `asyncio.gather()` 활용
- **max_turns 설정**: 무한 루프 방지
- **적절한 모델 선택**: 작업 복잡도에 맞는 모델 사용

### 5. Safety
- **Guardrails 활용**: 입력/출력 검증
- **민감 데이터 처리**: `trace_include_sensitive_data=False`
- **비용 제어**: max_turns, 저비용 모델로 검증

---

## Quick Reference

```python
from agents import (
    # Core
    Agent,
    Runner,
    RunConfig,

    # Tools
    function_tool,
    WebSearchTool,
    FileSearchTool,
    CodeInterpreterTool,

    # Handoffs
    handoff,

    # Guardrails
    input_guardrail,
    output_guardrail,
    GuardrailFunctionOutput,

    # Context
    RunContextWrapper,

    # Tracing
    trace,
    custom_span,

    # Exceptions
    MaxTurnsExceeded,
    ModelBehaviorError,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
)
```
