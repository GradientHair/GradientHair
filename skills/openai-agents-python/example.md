# OpenAI Agents Python SDK - Comprehensive Examples

이 문서는 다양한 multi-agent 시나리오에 대한 실제 구현 예제를 제공합니다.

---

## Example 1: Customer Support System

고객 지원 시스템 - Triage Agent가 문의를 분류하고 적절한 전문 에이전트로 라우팅합니다.

```python
from agents import Agent, Runner, handoff, function_tool
from pydantic import BaseModel
from dataclasses import dataclass
import asyncio

# Context 정의
@dataclass
class CustomerContext:
    customer_id: str
    customer_name: str
    subscription_tier: str
    order_history: list[str]

# Tools 정의
@function_tool
def get_order_status(order_id: str) -> str:
    """주문 상태를 조회합니다.

    Args:
        order_id: 조회할 주문 ID
    """
    # 실제로는 DB 조회
    return f"Order {order_id}: Shipped, expected delivery in 2 days"

@function_tool
def process_refund(order_id: str, reason: str) -> str:
    """환불을 처리합니다.

    Args:
        order_id: 환불할 주문 ID
        reason: 환불 사유
    """
    return f"Refund initiated for order {order_id}. Processing time: 3-5 business days"

@function_tool
def update_subscription(tier: str) -> str:
    """구독 등급을 변경합니다.

    Args:
        tier: 새로운 구독 등급 (basic, premium, enterprise)
    """
    return f"Subscription updated to {tier}. Changes effective immediately."

# 전문 에이전트들 정의
order_agent = Agent[CustomerContext](
    name="Order Specialist",
    instructions="""You are an order specialist.
    Help customers with:
    - Order status inquiries
    - Shipping information
    - Order modifications

    Be concise and helpful. Always provide order IDs when relevant.
    """,
    tools=[get_order_status]
)

refund_agent = Agent[CustomerContext](
    name="Refund Specialist",
    instructions="""You are a refund specialist.
    Help customers with:
    - Refund requests
    - Return policies
    - Refund status

    Be empathetic and explain the refund process clearly.
    """,
    tools=[process_refund]
)

billing_agent = Agent[CustomerContext](
    name="Billing Specialist",
    instructions="""You are a billing specialist.
    Help customers with:
    - Subscription changes
    - Payment issues
    - Invoice inquiries

    Always confirm changes with the customer before processing.
    """,
    tools=[update_subscription]
)

# Triage Agent (라우터)
triage_agent = Agent[CustomerContext](
    name="Customer Support Triage",
    instructions="""You are the first point of contact for customer support.

    Analyze the customer's inquiry and route to the appropriate specialist:
    - Order questions (status, shipping, modifications) → Order Specialist
    - Refund requests or returns → Refund Specialist
    - Billing, subscriptions, payments → Billing Specialist

    If the inquiry is general or you can answer directly, do so.
    Always greet the customer by name.
    """,
    handoffs=[order_agent, refund_agent, billing_agent]
)

# 실행
async def handle_customer_inquiry(customer_id: str, inquiry: str):
    context = CustomerContext(
        customer_id=customer_id,
        customer_name="John Doe",
        subscription_tier="premium",
        order_history=["ORD-001", "ORD-002", "ORD-003"]
    )

    result = await Runner.run(
        triage_agent,
        inquiry,
        context=context
    )

    return result.final_output

# 사용 예
if __name__ == "__main__":
    inquiry = "I want to check the status of my recent order ORD-003"
    response = asyncio.run(handle_customer_inquiry("CUST-123", inquiry))
    print(response)
```

---

## Example 2: Content Creation Pipeline

리서치 → 작성 → 편집 → 최종 검토 파이프라인입니다.

```python
from agents import Agent, Runner, function_tool
from pydantic import BaseModel
import asyncio

# 구조화된 출력 타입들
class ResearchResult(BaseModel):
    topic: str
    key_points: list[str]
    sources: list[str]
    suggested_structure: list[str]

class DraftContent(BaseModel):
    title: str
    introduction: str
    body: str
    conclusion: str

class EditSuggestions(BaseModel):
    overall_score: float
    strengths: list[str]
    improvements: list[str]
    revised_content: str

class FinalReview(BaseModel):
    approved: bool
    final_content: str
    seo_keywords: list[str]
    meta_description: str

# 에이전트들
researcher = Agent(
    name="Research Specialist",
    instructions="""You are a thorough researcher.
    When given a topic:
    1. Identify 5-7 key points to cover
    2. Suggest reliable source types
    3. Propose a logical content structure

    Focus on accuracy and comprehensiveness.
    """,
    output_type=ResearchResult
)

writer = Agent(
    name="Content Writer",
    instructions="""You are a skilled content writer.
    Based on research provided:
    1. Write engaging, clear content
    2. Follow the suggested structure
    3. Include all key points
    4. Maintain consistent tone

    Target audience: general readers interested in technology.
    Aim for ~500 words.
    """,
    output_type=DraftContent
)

editor = Agent(
    name="Editor",
    instructions="""You are a meticulous editor.
    Review the draft and:
    1. Score overall quality (0-10)
    2. Identify strengths
    3. Suggest specific improvements
    4. Provide a revised version

    Focus on clarity, flow, and engagement.
    """,
    output_type=EditSuggestions
)

final_reviewer = Agent(
    name="Final Reviewer",
    instructions="""You are the final quality gate.
    Review the edited content and:
    1. Approve if quality score >= 8
    2. Provide the final polished version
    3. Generate SEO keywords
    4. Write meta description

    Ensure content is publish-ready.
    """,
    output_type=FinalReview
)

# 파이프라인 실행
async def create_content(topic: str) -> FinalReview:
    print(f"📚 Starting content creation for: {topic}\n")

    # Step 1: Research
    print("🔍 Researching...")
    research_result = await Runner.run(researcher, f"Research the topic: {topic}")
    research: ResearchResult = research_result.final_output
    print(f"   Found {len(research.key_points)} key points\n")

    # Step 2: Write Draft
    print("✍️ Writing draft...")
    write_prompt = f"""
    Topic: {research.topic}

    Key Points to Cover:
    {chr(10).join(f'- {point}' for point in research.key_points)}

    Suggested Structure:
    {chr(10).join(f'{i+1}. {section}' for i, section in enumerate(research.suggested_structure))}
    """
    draft_result = await Runner.run(writer, write_prompt)
    draft: DraftContent = draft_result.final_output
    print(f"   Draft complete: '{draft.title}'\n")

    # Step 3: Edit
    print("📝 Editing...")
    full_draft = f"""
    Title: {draft.title}

    {draft.introduction}

    {draft.body}

    {draft.conclusion}
    """
    edit_result = await Runner.run(editor, f"Edit this draft:\n{full_draft}")
    edits: EditSuggestions = edit_result.final_output
    print(f"   Score: {edits.overall_score}/10\n")

    # Step 4: Final Review
    print("✅ Final review...")
    final_result = await Runner.run(
        final_reviewer,
        f"Review this edited content (score: {edits.overall_score}):\n{edits.revised_content}"
    )
    final: FinalReview = final_result.final_output

    status = "APPROVED ✓" if final.approved else "NEEDS REVISION"
    print(f"   Status: {status}\n")

    return final

# 사용 예
if __name__ == "__main__":
    result = asyncio.run(create_content("The Future of AI in Healthcare"))
    print("=" * 50)
    print(f"Final Content:\n{result.final_content[:500]}...")
    print(f"\nSEO Keywords: {', '.join(result.seo_keywords)}")
    print(f"Meta Description: {result.meta_description}")
```

---

## Example 3: Code Review System

코드 리뷰 multi-agent 시스템 - 보안, 성능, 스타일을 병렬로 검토합니다.

```python
from agents import Agent, Runner, function_tool
from pydantic import BaseModel
import asyncio

# 출력 타입들
class SecurityReview(BaseModel):
    severity: str  # low, medium, high, critical
    issues: list[str]
    recommendations: list[str]

class PerformanceReview(BaseModel):
    efficiency_score: float
    bottlenecks: list[str]
    optimizations: list[str]

class StyleReview(BaseModel):
    readability_score: float
    violations: list[str]
    suggestions: list[str]

class FinalCodeReview(BaseModel):
    overall_score: float
    approved: bool
    summary: str
    critical_issues: list[str]
    all_recommendations: list[str]

# 전문 리뷰어 에이전트들
security_reviewer = Agent(
    name="Security Reviewer",
    instructions="""You are a security expert reviewing code.
    Look for:
    - SQL injection vulnerabilities
    - XSS vulnerabilities
    - Hardcoded secrets
    - Authentication/authorization issues
    - Input validation problems
    - Insecure dependencies

    Be thorough and provide actionable recommendations.
    """,
    output_type=SecurityReview
)

performance_reviewer = Agent(
    name="Performance Reviewer",
    instructions="""You are a performance engineer reviewing code.
    Look for:
    - N+1 query problems
    - Unnecessary loops or iterations
    - Memory leaks
    - Inefficient algorithms
    - Missing caching opportunities
    - Blocking operations

    Score efficiency from 0-10 and suggest optimizations.
    """,
    output_type=PerformanceReview
)

style_reviewer = Agent(
    name="Style Reviewer",
    instructions="""You are a code quality expert.
    Review for:
    - Naming conventions
    - Code organization
    - Documentation quality
    - DRY principle violations
    - SOLID principle adherence
    - Error handling patterns

    Score readability from 0-10.
    """,
    output_type=StyleReview
)

# 최종 리뷰어 (결과 종합)
final_reviewer = Agent(
    name="Lead Reviewer",
    instructions="""You are the lead code reviewer.
    Synthesize all review feedback into a final assessment.

    Scoring criteria:
    - If any critical security issues: overall score < 5
    - If efficiency < 5: reduce 2 points
    - If readability < 5: reduce 1 point

    Approve if overall score >= 7 and no critical security issues.
    """,
    output_type=FinalCodeReview
)

# 병렬 리뷰 실행
async def review_code(code: str) -> FinalCodeReview:
    print("🔍 Starting parallel code review...\n")

    # 병렬로 모든 리뷰 실행
    security_task = Runner.run(security_reviewer, f"Review this code for security:\n```\n{code}\n```")
    performance_task = Runner.run(performance_reviewer, f"Review this code for performance:\n```\n{code}\n```")
    style_task = Runner.run(style_reviewer, f"Review this code for style:\n```\n{code}\n```")

    results = await asyncio.gather(security_task, performance_task, style_task)

    security: SecurityReview = results[0].final_output
    performance: PerformanceReview = results[1].final_output
    style: StyleReview = results[2].final_output

    print(f"🔒 Security: {security.severity} severity")
    print(f"⚡ Performance: {performance.efficiency_score}/10")
    print(f"📐 Style: {style.readability_score}/10\n")

    # 최종 리뷰
    synthesis_prompt = f"""
    Synthesize these code review results:

    SECURITY REVIEW:
    - Severity: {security.severity}
    - Issues: {security.issues}
    - Recommendations: {security.recommendations}

    PERFORMANCE REVIEW:
    - Efficiency Score: {performance.efficiency_score}/10
    - Bottlenecks: {performance.bottlenecks}
    - Optimizations: {performance.optimizations}

    STYLE REVIEW:
    - Readability Score: {style.readability_score}/10
    - Violations: {style.violations}
    - Suggestions: {style.suggestions}
    """

    final_result = await Runner.run(final_reviewer, synthesis_prompt)
    return final_result.final_output

# 사용 예
if __name__ == "__main__":
    sample_code = '''
    def get_user(user_id):
        query = f"SELECT * FROM users WHERE id = {user_id}"
        result = db.execute(query)
        users = []
        for row in result:
            user = User(row)
            user.orders = db.execute(f"SELECT * FROM orders WHERE user_id = {row.id}")
            users.append(user)
        return users
    '''

    review = asyncio.run(review_code(sample_code))
    print("=" * 50)
    print(f"Overall Score: {review.overall_score}/10")
    print(f"Approved: {'✅' if review.approved else '❌'}")
    print(f"\nSummary: {review.summary}")
    if review.critical_issues:
        print(f"\n⚠️ Critical Issues:")
        for issue in review.critical_issues:
            print(f"  - {issue}")
```

---

## Example 4: Data Analysis Pipeline with Guardrails

데이터 분석 파이프라인 - 입력 검증과 출력 검증을 포함합니다.

```python
from agents import (
    Agent, Runner, RunConfig,
    function_tool, input_guardrail, output_guardrail,
    GuardrailFunctionOutput
)
from pydantic import BaseModel
import asyncio

# 출력 타입
class AnalysisResult(BaseModel):
    summary: str
    insights: list[str]
    recommendations: list[str]
    confidence_score: float
    data_quality_score: float

# Guardrails
@input_guardrail
async def validate_data_input(ctx, agent, input) -> GuardrailFunctionOutput:
    """입력 데이터 검증"""
    # 민감 정보 체크
    sensitive_patterns = ["ssn", "social security", "credit card", "password"]
    has_sensitive = any(pattern in str(input).lower() for pattern in sensitive_patterns)

    # 데이터 크기 체크
    is_too_large = len(str(input)) > 100000

    return GuardrailFunctionOutput(
        output_info={
            "has_sensitive_data": has_sensitive,
            "is_too_large": is_too_large
        },
        tripwire_triggered=has_sensitive or is_too_large
    )

@output_guardrail
async def validate_analysis_output(ctx, agent, output) -> GuardrailFunctionOutput:
    """출력 품질 검증"""
    if isinstance(output, AnalysisResult):
        # 신뢰도가 너무 낮으면 거부
        low_confidence = output.confidence_score < 0.5
        # 인사이트가 없으면 거부
        no_insights = len(output.insights) == 0

        return GuardrailFunctionOutput(
            output_info={
                "confidence": output.confidence_score,
                "insight_count": len(output.insights)
            },
            tripwire_triggered=low_confidence or no_insights
        )

    return GuardrailFunctionOutput(
        output_info={"type": type(output).__name__},
        tripwire_triggered=False
    )

# Tools
@function_tool
def calculate_statistics(data: str) -> str:
    """데이터의 기본 통계를 계산합니다.

    Args:
        data: 분석할 데이터 (JSON 형식)
    """
    # 실제 구현에서는 pandas 등 사용
    return """
    Statistics:
    - Count: 1000 records
    - Mean: 45.2
    - Std Dev: 12.3
    - Min: 10, Max: 95
    - Missing values: 2.3%
    """

@function_tool
def detect_anomalies(data: str, threshold: float = 2.0) -> str:
    """데이터에서 이상치를 탐지합니다.

    Args:
        data: 분석할 데이터
        threshold: Z-score 임계값 (기본값 2.0)
    """
    return """
    Anomalies detected:
    - 15 outliers found (1.5% of data)
    - Cluster at indices: [23, 156, 789, ...]
    - Potential causes: data entry errors, exceptional cases
    """

@function_tool
def generate_visualization_spec(chart_type: str, data_fields: list[str]) -> str:
    """시각화 사양을 생성합니다.

    Args:
        chart_type: 차트 유형 (bar, line, scatter, heatmap)
        data_fields: 시각화할 필드들
    """
    return f"""
    Visualization Spec:
    - Type: {chart_type}
    - Fields: {data_fields}
    - Recommended dimensions: 800x600
    - Color scheme: viridis
    """

# 분석 에이전트
data_analyst = Agent(
    name="Data Analyst",
    instructions="""You are an expert data analyst.
    When analyzing data:
    1. First calculate basic statistics
    2. Detect any anomalies
    3. Generate insights based on patterns
    4. Provide actionable recommendations
    5. Rate your confidence in the analysis

    Be thorough but concise. Focus on actionable insights.
    """,
    tools=[calculate_statistics, detect_anomalies, generate_visualization_spec],
    output_type=AnalysisResult,
    input_guardrails=[validate_data_input],
    output_guardrails=[validate_analysis_output]
)

# 실행
async def analyze_data(data: str):
    try:
        result = await Runner.run(
            data_analyst,
            f"Analyze this data and provide insights:\n{data}",
            run_config=RunConfig(max_turns=10)
        )
        return result.final_output
    except Exception as e:
        if "InputGuardrailTripwireTriggered" in str(type(e)):
            return "Error: Input contains sensitive data or is too large"
        elif "OutputGuardrailTripwireTriggered" in str(type(e)):
            return "Error: Analysis quality too low, please provide better data"
        raise

# 사용 예
if __name__ == "__main__":
    sample_data = """
    Monthly Sales Data:
    Jan: 45000, Feb: 52000, Mar: 48000, Apr: 61000,
    May: 58000, Jun: 72000, Jul: 69000, Aug: 75000,
    Sep: 82000, Oct: 79000, Nov: 95000, Dec: 120000
    """

    result = asyncio.run(analyze_data(sample_data))
    if isinstance(result, AnalysisResult):
        print(f"Summary: {result.summary}")
        print(f"\nInsights:")
        for insight in result.insights:
            print(f"  - {insight}")
        print(f"\nConfidence: {result.confidence_score:.1%}")
    else:
        print(result)
```

---

## Example 5: Interactive Task Manager with Human-in-the-Loop

사용자 확인이 필요한 작업을 처리하는 시스템입니다.

```python
from agents import Agent, Runner, function_tool, handoff
from pydantic import BaseModel
from typing import Optional
import asyncio

# 승인 대기 상태 관리
pending_approvals = {}

class TaskAction(BaseModel):
    action: str  # create, update, delete, assign
    task_id: Optional[str]
    details: dict
    requires_approval: bool
    approval_reason: Optional[str]

# Tools
@function_tool
def list_tasks(status: str = "all") -> str:
    """현재 태스크 목록을 조회합니다.

    Args:
        status: 필터링할 상태 (all, pending, in_progress, done)
    """
    return """
    Tasks:
    1. [TASK-001] Implement login (in_progress) - assigned to: Alice
    2. [TASK-002] Fix payment bug (pending) - assigned to: Bob
    3. [TASK-003] Update docs (done) - assigned to: Carol
    4. [TASK-004] Deploy to prod (pending) - unassigned
    """

@function_tool
def create_task(title: str, description: str, priority: str) -> str:
    """새 태스크를 생성합니다.

    Args:
        title: 태스크 제목
        description: 상세 설명
        priority: 우선순위 (low, medium, high, critical)
    """
    return f"Task created: TASK-005 - {title} (Priority: {priority})"

@function_tool
def assign_task(task_id: str, assignee: str) -> str:
    """태스크를 담당자에게 할당합니다.

    Args:
        task_id: 태스크 ID
        assignee: 담당자 이름
    """
    return f"Task {task_id} assigned to {assignee}"

@function_tool
def request_approval(action: str, details: str) -> str:
    """관리자 승인을 요청합니다.

    Args:
        action: 승인이 필요한 작업 유형
        details: 작업 상세 내용
    """
    approval_id = f"APR-{len(pending_approvals) + 1:03d}"
    pending_approvals[approval_id] = {"action": action, "details": details, "status": "pending"}
    return f"Approval requested: {approval_id}. Waiting for manager approval."

@function_tool
def delete_task(task_id: str, reason: str) -> str:
    """태스크를 삭제합니다. (관리자 승인 필요)

    Args:
        task_id: 삭제할 태스크 ID
        reason: 삭제 사유
    """
    # 실제로는 승인 후 삭제
    return f"Task {task_id} marked for deletion. Reason: {reason}. Pending approval."

# 에이전트들
task_agent = Agent(
    name="Task Manager",
    instructions="""You are a task management assistant.
    You can:
    - List and search tasks
    - Create new tasks
    - Assign tasks to team members

    For sensitive operations (delete, bulk changes), request approval first.
    Always confirm actions with the user.
    """,
    tools=[list_tasks, create_task, assign_task, request_approval]
)

admin_agent = Agent(
    name="Admin Agent",
    instructions="""You are an admin assistant with elevated privileges.
    You can:
    - Delete tasks (with approval)
    - Modify system settings
    - View audit logs

    Always explain the impact of admin actions.
    """,
    tools=[delete_task, list_tasks]
)

# 메인 에이전트 (라우터)
main_agent = Agent(
    name="Project Assistant",
    instructions="""You are a project management assistant.

    For regular task operations, handle them directly.
    For admin operations (delete, system changes), hand off to Admin Agent.

    Always be helpful and explain what you're doing.
    """,
    handoffs=[task_agent, admin_agent]
)

# 대화형 세션
async def interactive_session():
    conversation_history = []

    print("🤖 Project Assistant: Hello! I can help you manage tasks.")
    print("   Commands: list, create, assign, delete, or just describe what you need.")
    print("   Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'quit':
            print("👋 Goodbye!")
            break

        # 대화 이력에 추가
        conversation_history.append({"role": "user", "content": user_input})

        # 에이전트 실행
        result = await Runner.run(main_agent, conversation_history)

        # 응답 출력
        print(f"\n🤖 Assistant: {result.final_output}\n")

        # 대화 이력 업데이트
        conversation_history = result.to_input_list()

# 사용 예
if __name__ == "__main__":
    asyncio.run(interactive_session())
```

---

## Example 6: Research Assistant with Web Search

웹 검색과 요약 기능을 갖춘 리서치 어시스턴트입니다.

```python
from agents import Agent, Runner
from agents.tools import WebSearchTool
from pydantic import BaseModel
import asyncio

# 출력 타입
class ResearchReport(BaseModel):
    topic: str
    executive_summary: str
    key_findings: list[str]
    detailed_sections: list[dict]
    sources: list[str]
    further_research: list[str]

# 에이전트들
web_researcher = Agent(
    name="Web Researcher",
    instructions="""You are a web researcher.
    Search for relevant, recent, and reliable information.
    Focus on:
    - Official sources
    - Recent publications (prefer last 2 years)
    - Multiple perspectives

    Provide source URLs for all information.
    """,
    tools=[WebSearchTool()]
)

synthesizer = Agent(
    name="Research Synthesizer",
    instructions="""You are a research synthesizer.
    Take raw research findings and:
    1. Remove duplicate information
    2. Identify key themes and patterns
    3. Organize into logical sections
    4. Highlight contradictions or debates
    5. Suggest areas for further research

    Be objective and cite sources.
    """,
    output_type=ResearchReport
)

# Manager 패턴으로 구성
research_manager = Agent(
    name="Research Manager",
    instructions="""You are a research project manager.

    When given a research topic:
    1. Use the web_researcher to gather information
    2. Use the synthesizer to create a structured report

    Ensure comprehensive coverage of the topic.
    """,
    tools=[
        web_researcher.as_tool(
            tool_name="search_web",
            tool_description="Search the web for information on a topic"
        ),
        synthesizer.as_tool(
            tool_name="synthesize_research",
            tool_description="Synthesize research findings into a structured report"
        )
    ]
)

# 실행
async def conduct_research(topic: str) -> ResearchReport:
    print(f"🔬 Starting research on: {topic}\n")

    result = await Runner.run(
        research_manager,
        f"Conduct comprehensive research on: {topic}"
    )

    return result.final_output

# 사용 예
if __name__ == "__main__":
    topic = "Latest developments in quantum computing 2024"
    report = asyncio.run(conduct_research(topic))

    print("=" * 60)
    print(f"📋 RESEARCH REPORT: {report.topic}")
    print("=" * 60)
    print(f"\n📌 Executive Summary:\n{report.executive_summary}")
    print(f"\n🔑 Key Findings:")
    for finding in report.key_findings:
        print(f"  • {finding}")
    print(f"\n📚 Sources: {len(report.sources)} references")
```

---

## Example 7: Multi-Language Translation Service

병렬 번역과 품질 검증을 포함한 번역 서비스입니다.

```python
from agents import Agent, Runner, function_tool
from pydantic import BaseModel
import asyncio

class TranslationResult(BaseModel):
    original: str
    source_language: str
    translations: dict[str, str]
    quality_scores: dict[str, float]
    notes: list[str]

# 언어별 번역 에이전트 생성 함수
def create_translator(language: str, language_name: str) -> Agent:
    return Agent(
        name=f"{language_name} Translator",
        instructions=f"""You are a professional {language_name} translator.
        Translate the given text to {language_name}.
        - Maintain the original tone and style
        - Adapt idioms appropriately
        - Preserve formatting
        Only output the translation, nothing else.
        """
    )

# 번역기들 생성
translators = {
    "ko": create_translator("ko", "Korean"),
    "ja": create_translator("ja", "Japanese"),
    "zh": create_translator("zh", "Chinese"),
    "es": create_translator("es", "Spanish"),
    "fr": create_translator("fr", "French"),
}

# 품질 검증 에이전트
quality_checker = Agent(
    name="Translation QA",
    instructions="""You are a translation quality assessor.
    Rate translations on a scale of 1-10 based on:
    - Accuracy (40%)
    - Fluency (30%)
    - Style preservation (30%)

    Output only the numeric score.
    """
)

# 오케스트레이터
async def translate_to_multiple_languages(
    text: str,
    target_languages: list[str]
) -> TranslationResult:
    print(f"🌐 Translating to {len(target_languages)} languages...\n")

    # 병렬 번역
    translation_tasks = []
    for lang in target_languages:
        if lang in translators:
            task = Runner.run(translators[lang], f"Translate:\n{text}")
            translation_tasks.append((lang, task))

    # 번역 결과 수집
    translations = {}
    for lang, task in translation_tasks:
        result = await task
        translations[lang] = result.final_output
        print(f"  ✓ {lang}: completed")

    # 병렬 품질 검증
    print("\n📊 Checking quality...")
    quality_tasks = []
    for lang, translation in translations.items():
        prompt = f"Original: {text}\n\nTranslation ({lang}): {translation}\n\nRate quality (1-10):"
        task = Runner.run(quality_checker, prompt)
        quality_tasks.append((lang, task))

    quality_scores = {}
    for lang, task in quality_tasks:
        result = await task
        try:
            score = float(result.final_output.strip())
            quality_scores[lang] = min(10, max(1, score))
        except:
            quality_scores[lang] = 0.0

    # 결과 종합
    notes = []
    for lang, score in quality_scores.items():
        if score < 7:
            notes.append(f"Warning: {lang} translation may need review (score: {score})")

    return TranslationResult(
        original=text,
        source_language="en",
        translations=translations,
        quality_scores=quality_scores,
        notes=notes
    )

# 사용 예
if __name__ == "__main__":
    text = "The early bird catches the worm, but the second mouse gets the cheese."
    result = asyncio.run(translate_to_multiple_languages(text, ["ko", "ja", "es"]))

    print("\n" + "=" * 50)
    print(f"Original: {result.original}\n")
    for lang, translation in result.translations.items():
        score = result.quality_scores.get(lang, "N/A")
        print(f"[{lang}] (Score: {score}/10)")
        print(f"  {translation}\n")
```

---

## Example 8: Error Recovery and Retry Pattern

에러 처리와 재시도 로직을 포함한 견고한 에이전트 시스템입니다.

```python
from agents import Agent, Runner, RunConfig, function_tool
from agents import MaxTurnsExceeded, ModelBehaviorError
import asyncio
from typing import Optional

# 실패할 수 있는 도구
@function_tool
def unreliable_api_call(endpoint: str) -> str:
    """외부 API를 호출합니다. 가끔 실패할 수 있습니다.

    Args:
        endpoint: API 엔드포인트
    """
    import random
    if random.random() < 0.3:  # 30% 실패율
        raise Exception(f"API call to {endpoint} failed: Connection timeout")
    return f"Success: Data from {endpoint}"

@function_tool(failure_error_function=lambda ctx, e: f"API temporarily unavailable: {e}. Please try again.")
def api_with_graceful_error(endpoint: str) -> str:
    """에러 처리가 포함된 API 호출.

    Args:
        endpoint: API 엔드포인트
    """
    import random
    if random.random() < 0.3:
        raise Exception("Connection refused")
    return f"Data retrieved from {endpoint}"

# 재시도 로직이 포함된 에이전트 실행
async def run_with_retry(
    agent: Agent,
    input: str,
    max_retries: int = 3,
    backoff_factor: float = 1.5
) -> Optional[str]:
    """재시도 로직이 포함된 에이전트 실행"""
    last_error = None

    for attempt in range(max_retries):
        try:
            result = await Runner.run(
                agent,
                input,
                run_config=RunConfig(max_turns=10)
            )
            return result.final_output

        except MaxTurnsExceeded:
            print(f"⚠️ Attempt {attempt + 1}: Max turns exceeded")
            last_error = "Agent exceeded maximum turns"

        except ModelBehaviorError as e:
            print(f"⚠️ Attempt {attempt + 1}: Model error - {e}")
            last_error = str(e)

        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1}: Error - {e}")
            last_error = str(e)

        # 대기 (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = backoff_factor ** attempt
            print(f"   Retrying in {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)

    print(f"❌ All {max_retries} attempts failed. Last error: {last_error}")
    return None

# Fallback 에이전트 패턴
primary_agent = Agent(
    name="Primary Agent",
    instructions="You are the primary agent. Use the API to get data.",
    tools=[unreliable_api_call],
    model="gpt-4o"
)

fallback_agent = Agent(
    name="Fallback Agent",
    instructions="You are the fallback agent. Provide cached or default responses.",
    model="gpt-4o-mini"  # 더 저렴한 모델
)

async def execute_with_fallback(input: str) -> str:
    """Primary 실패 시 Fallback 사용"""
    print("🚀 Trying primary agent...")
    result = await run_with_retry(primary_agent, input, max_retries=2)

    if result:
        return result

    print("\n🔄 Falling back to secondary agent...")
    fallback_result = await Runner.run(
        fallback_agent,
        f"The primary system is unavailable. Please provide a helpful response for: {input}"
    )
    return f"[Fallback Response] {fallback_result.final_output}"

# 사용 예
if __name__ == "__main__":
    result = asyncio.run(execute_with_fallback("Get the latest sales data"))
    print(f"\n📋 Final Result: {result}")
```

---

## Quick Reference: Common Patterns

### 1. 간단한 단일 에이전트
```python
agent = Agent(name="Simple", instructions="...")
result = await Runner.run(agent, "Hello")
```

### 2. 도구가 있는 에이전트
```python
@function_tool
def my_tool(arg: str) -> str:
    """Tool description."""
    return f"Result: {arg}"

agent = Agent(name="With Tools", tools=[my_tool])
```

### 3. Handoff 패턴
```python
specialist = Agent(name="Specialist", instructions="...")
router = Agent(name="Router", handoffs=[specialist])
```

### 4. Manager 패턴 (Agent as Tool)
```python
worker = Agent(name="Worker", instructions="...")
manager = Agent(
    name="Manager",
    tools=[worker.as_tool(tool_name="delegate", tool_description="...")]
)
```

### 5. 병렬 실행
```python
results = await asyncio.gather(
    Runner.run(agent1, input1),
    Runner.run(agent2, input2),
)
```

### 6. 구조화된 출력
```python
class Output(BaseModel):
    field: str

agent = Agent(name="Structured", output_type=Output)
result = await Runner.run(agent, "...")
typed_output: Output = result.final_output
```

### 7. 대화 유지
```python
result1 = await Runner.run(agent, "First message")
result2 = await Runner.run(agent, result1.to_input_list() + [{"role": "user", "content": "Follow up"}])
```
