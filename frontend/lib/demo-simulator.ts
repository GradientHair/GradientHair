import { soundPlayer } from "./sound-player";

export interface DemoScriptEntry {
  speaker: string;
  text: string;
  delay: number;
  triggerIntervention?: string;
  interventionMessage?: string;
}

type InterventionPayload = {
  id: string;
  type: string;
  message: string;
  parkingLotItem?: string;
  violatedPrinciple?: string;
  suggestedSpeaker?: string;
};

type DemoContext = {
  agendaTopic: string;
  driftTopic: string;
  driftLine: string;
  driftParkingLot: string;
  driftInterventionMessage: string;
  violatedPrinciple: string;
  principleViolationLine: string;
  principleViolationMessage: string;
  decisionLeadLine: string;
  decisionFollowLine: string;
  decisionInterventionMessage: string;
  silentSpeaker: string;
  silentSpeakerRole: string;
  supportingSpeaker: string;
};

type DemoParticipant = {
  name: string;
  role: string;
};

type DemoSimulatorOptions = {
  agenda?: string;
  participants?: DemoParticipant[];
  persona?: string;
  useLLM?: boolean;
};

const roleBySpeaker: Record<string, string> = {
  김철수: "PM",
  이민수: "프론트엔드",
  박영희: "백엔드",
  최지은: "디자인",
};

const agendaTopics = ["스프린트 계획", "스프린트 회고", "Q1 목표 정리"];
const driftScenarios = [
  {
    topic: "점심 메뉴",
    line: "그런데 점심 뭐 먹을까요? 회사 앞에 새로 생긴 라멘집이 맛있다던데요.",
    buildMessage: (agendaTopic: string, topic: string) =>
      `잠깐요, 아젠다에서 벗어났어요. '${agendaTopic}'으로 돌아갈게요. ${topic}는 Parking Lot에 추가했습니다.`,
  },
  {
    topic: "캐시 TTL",
    line: "Redis 캐시 TTL을 5분으로 하면 어떨까요? 키 구조도 먼저 정해야 합니다.",
    buildMessage: (agendaTopic: string, topic: string) =>
      `지금은 '${agendaTopic}' 같은 방향을 정하는 시간이에요. ${topic} 같은 구현 디테일은 Parking Lot에 기록하고 다음 기술 회의로 옮길게요.`,
  },
  {
    topic: "채용 소식",
    line: "아, 오늘 채용 공고 올라간 거 보셨어요? 추천할 사람 있나요?",
    buildMessage: (agendaTopic: string, topic: string) =>
      `잠깐요, 아젠다에서 벗어났어요. '${agendaTopic}'으로 돌아갈게요. ${topic}는 Parking Lot에 추가했습니다.`,
  },
];
const decisionScenarios = [
  {
    leadLine: "A안이 낫긴 한데 리소스가 걱정돼요.",
    followLine: "B안도 괜찮은데 결정은 다음에 하죠.",
    message:
      "정리할게요. 오늘은 'A안 vs B안' 비교만 하고 결정은 다음 회의로 넘길까요? 다음 회의 전까지 필요한 데이터가 무엇인지 정해요.",
  },
  {
    leadLine: "지금은 방향만 잡고 세부사항은 다음에 논의하죠.",
    followLine: "그럼 오늘 확정할 건 없는 건가요?",
    message:
      "오늘 확정할 항목을 한 줄로 정리할게요. 없으면 다음 회의의 결정 기준과 준비 자료를 명확히 하죠.",
  },
];

const pick = <T,>(items: T[]): T => items[Math.floor(Math.random() * items.length)];

const buildDemoContext = (): DemoContext => {
  const agendaTopic = pick(agendaTopics);
  const driftPick = pick(driftScenarios);
  const decisionPick = pick(decisionScenarios);
  const violationMode = pick(["top_down", "aggressive"] as const);
  const violatedPrinciple = violationMode === "aggressive" ? "심리적 안전" : "수평적 의사결정";
  const silentSpeaker = pick(["박영희", "최지은"]);
  const supportingSpeaker = silentSpeaker === "박영희" ? "최지은" : "박영희";
  const silentSpeakerRole = roleBySpeaker[silentSpeaker] || "팀원";

  const principleViolationLine =
    violationMode === "aggressive"
      ? "이건 전적으로 개발팀 책임이에요. 왜 이렇게 기본도 안 돼 있죠?"
      : "이건 제가 결정했으니까, 다들 이대로 진행해 주세요.";
  const principleViolationMessage =
    violationMode === "aggressive"
      ? "잠깐요, 표현이 공격적으로 들릴 수 있어요. 사람보다 문제에 집중하고 원인을 같이 정리해 볼까요?"
      : `멈춰주세요! '${violatedPrinciple}' 원칙 위반입니다. 혼자 결정하시면 안 돼요. 다른 분들 동의하시나요?`;

  return {
    agendaTopic,
    driftTopic: driftPick.topic,
    driftLine: driftPick.line,
    driftParkingLot: driftPick.topic,
    driftInterventionMessage: driftPick.buildMessage(agendaTopic, driftPick.topic),
    violatedPrinciple,
    principleViolationLine,
    principleViolationMessage,
    decisionLeadLine: decisionPick.leadLine,
    decisionFollowLine: decisionPick.followLine,
    decisionInterventionMessage: decisionPick.message,
    silentSpeaker,
    silentSpeakerRole,
    supportingSpeaker,
  };
};

const buildInterventionMessages = (context: DemoContext): Record<string, InterventionPayload> => ({
  TOPIC_DRIFT: {
    id: "int_demo_001",
    type: "TOPIC_DRIFT",
    message: context.driftInterventionMessage,
    parkingLotItem: context.driftParkingLot,
  },
  PRINCIPLE_VIOLATION: {
    id: "int_demo_002",
    type: "PRINCIPLE_VIOLATION",
    message: context.principleViolationMessage,
    violatedPrinciple: context.principleViolationMessage.includes("원칙 위반")
      ? context.violatedPrinciple
      : "심리적 안전",
  },
  PARTICIPATION_IMBALANCE: {
    id: "int_demo_003",
    type: "PARTICIPATION_IMBALANCE",
    message: `잠깐요! ${context.silentSpeaker} 님 아직 한 번도 발언 안 하셨어요. ${context.silentSpeakerRole} 관점에서 어떻게 보세요?`,
    suggestedSpeaker: context.silentSpeaker,
  },
  DECISION_STYLE: {
    id: "int_demo_004",
    type: "DECISION_STYLE",
    message: context.decisionInterventionMessage,
  },
  FACILITATOR_CHECK: {
    id: "int_demo_005",
    type: "FACILITATOR_CHECK",
    message: "퍼실리테이터 확인: 발언 내용을 점검합니다.",
  },
});

const buildDemoScript = (context: DemoContext): DemoScriptEntry[] => [
  { speaker: "김철수", text: `지난 스프린트에서 주요 목표를 달성했습니다. 먼저 ${context.agendaTopic}부터 정리할게요.`, delay: 0 },
  { speaker: "이민수", text: "네, 특히 로그인 성능 개선이 눈에 띄었습니다. 데이터도 공유드릴게요.", delay: 3000 },
  { speaker: "김철수", text: "다음 스프린트에서는 온보딩 이탈률을 줄이는 쪽으로 집중하면 좋겠습니다.", delay: 6000 },
  { speaker: "이민수", text: context.driftLine, delay: 10000, triggerIntervention: "TOPIC_DRIFT" },
  { speaker: "김철수", text: `좋아요. 다시 ${context.agendaTopic}로 돌아가서 우선순위를 정하죠.`, delay: 16000 },
  { speaker: "김철수", text: "이번 스프린트는 API 응답 속도 개선을 1순위로 두겠습니다.", delay: 20000 },
  { speaker: "김철수", text: context.principleViolationLine, delay: 24000, triggerIntervention: "PRINCIPLE_VIOLATION" },
  { speaker: context.supportingSpeaker, text: "네, 우선 그렇게 진행하겠습니다.", delay: 30000 },
  { speaker: "이민수", text: context.decisionLeadLine, delay: 32000 },
  { speaker: "김철수", text: context.decisionFollowLine, delay: 36000, triggerIntervention: "DECISION_STYLE" },
  { speaker: "김철수", text: "좋습니다. 그럼 다음 주까지 각자 태스크 정리해주세요.", delay: 41000, triggerIntervention: "PARTICIPATION_IMBALANCE" },
];

const clampSummary = (text: string, limit = 80) => {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 3)}...`;
};

const buildPersonaFallbackLines = (persona: string, agenda: string, participants: DemoParticipant[]): DemoScriptEntry[] => {
  const speaker = participants[0]?.name || "김철수";
  const role = participants[0]?.role || "PM";
  const base = [
    `${agenda}에 대해 ${persona} 톤으로 바로 정리할게요.`,
    `핵심은 ${agenda}에서 가장 큰 리스크를 먼저 제거하는 겁니다.`,
    `${role} 관점에서 지금 당장 할 일은 우선순위 2~3개로 압축하는 거예요.`,
  ];
  return base.map((text, index) => ({
    speaker,
    text,
    delay: index * 3000,
    triggerIntervention: "FACILITATOR_CHECK",
    interventionMessage: `퍼실리테이터 확인: ${clampSummary(text)}`,
  }));
};

const buildPersonaScript = async (
  options: DemoSimulatorOptions
): Promise<DemoScriptEntry[]> => {
  const agenda = options.agenda?.trim() || "스프린트 계획";
  const persona = options.persona?.trim() || "직설적이고 빠른 의사결정";
  const participants = options.participants?.length
    ? options.participants
    : [
        { name: "김철수", role: "PM" },
        { name: "이민수", role: "프론트엔드" },
        { name: "박영희", role: "백엔드" },
        { name: "최지은", role: "디자인" },
      ];

  if (options.useLLM === false) {
    return buildPersonaFallbackLines(persona, agenda, participants);
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  if (!apiBase) {
    return buildPersonaFallbackLines(persona, agenda, participants);
  }

  try {
    const response = await fetch(`${apiBase}/demo/utterances`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agenda,
        persona,
        participants,
        count: 3,
      }),
    });

    if (!response.ok) {
      return buildPersonaFallbackLines(persona, agenda, participants);
    }

    const data = (await response.json()) as { utterances?: { speaker: string; text: string }[] };
    const utterances = data.utterances?.length ? data.utterances : null;
    if (!utterances) {
      return buildPersonaFallbackLines(persona, agenda, participants);
    }

    return utterances.map((entry, index) => ({
      speaker: entry.speaker,
      text: entry.text,
      delay: index * 3000,
      triggerIntervention: "FACILITATOR_CHECK",
      interventionMessage: `퍼실리테이터 확인: ${clampSummary(entry.text)}`,
    }));
  } catch {
    return buildPersonaFallbackLines(persona, agenda, participants);
  }
};

export class DemoSimulator {
  private timeouts: NodeJS.Timeout[] = [];
  private isRunning = false;
  private script: DemoScriptEntry[];
  private interventionMessages: Record<string, InterventionPayload>;
  private options: DemoSimulatorOptions;
  private onTranscript: (entry: {
    id: string;
    speaker: string;
    text: string;
    timestamp: string;
  }) => void;
  private onIntervention: (intervention: {
    id: string;
    type: string;
    message: string;
    timestamp: string;
    violatedPrinciple?: string;
    parkingLotItem?: string;
    suggestedSpeaker?: string;
  }) => void;

  constructor(
    onTranscript: (entry: {
      id: string;
      speaker: string;
      text: string;
      timestamp: string;
    }) => void,
    onIntervention: (intervention: {
      id: string;
      type: string;
      message: string;
      timestamp: string;
      violatedPrinciple?: string;
      parkingLotItem?: string;
      suggestedSpeaker?: string;
    }) => void,
    options: DemoSimulatorOptions = {}
  ) {
    this.onTranscript = onTranscript;
    this.onIntervention = onIntervention;
    this.options = options;
    const context = buildDemoContext();
    this.script = buildDemoScript(context);
    this.interventionMessages = buildInterventionMessages(context);
  }

  start() {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;

    buildPersonaScript(this.options).then((personaScript) => {
      if (!this.isRunning) {
        return;
      }

      const personaOffset = personaScript.length
        ? personaScript[personaScript.length - 1].delay + 2000
        : 0;
      const combinedScript = [
        ...personaScript,
        ...this.script.map((entry) => ({
          ...entry,
          delay: entry.delay + personaOffset,
        })),
      ];

      combinedScript.forEach((entry, index) => {
        const timeout = setTimeout(() => {
          if (!this.isRunning) return;

          this.onTranscript({
            id: `tr_demo_${index}`,
            speaker: entry.speaker,
            text: entry.text,
            timestamp: new Date().toISOString(),
          });

          if (entry.triggerIntervention) {
            const interventionTimeout = setTimeout(() => {
              if (!this.isRunning) return;

              soundPlayer.playAlert();
              this.onIntervention({
                ...(entry.interventionMessage
                  ? {
                      id: `int_demo_${index}`,
                      type: entry.triggerIntervention!,
                      message: entry.interventionMessage,
                    }
                  : this.interventionMessages[entry.triggerIntervention!]),
                timestamp: new Date().toISOString(),
              });
            }, 1200);

            // Track the nested timeout for cleanup
            this.timeouts.push(interventionTimeout);
          }
        }, entry.delay);

        this.timeouts.push(timeout);
      });
    });
  }

  stop() {
    this.isRunning = false;
    this.timeouts.forEach(clearTimeout);
    this.timeouts = [];
  }
}
