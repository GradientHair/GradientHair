import { soundPlayer } from "./sound-player";

export interface DemoScriptEntry {
  speaker: string;
  text: string;
  delay: number;
  triggerIntervention?: string;
}

export const demoScript: DemoScriptEntry[] = [
  { speaker: "김철수", text: "지난 스프린트에서 8개 태스크를 완료했습니다.", delay: 0 },
  { speaker: "이민수", text: "네, 성과가 좋았어요. 특히 로그인 개선이 효과적이었습니다.", delay: 3000 },
  { speaker: "김철수", text: "다음 스프린트에서는 온보딩 플로우를 개선하려고 합니다.", delay: 6000 },
  { speaker: "이민수", text: "그런데 점심 뭐 먹을까요? 회사 앞에 새로 생긴 라멘집이 맛있다던데.", delay: 10000, triggerIntervention: "TOPIC_DRIFT" },
  { speaker: "김철수", text: "아, 네. 다음 스프린트 계획을 보면...", delay: 18000 },
  { speaker: "김철수", text: "이번 스프린트는 API 최적화에 집중합시다.", delay: 22000 },
  { speaker: "김철수", text: "이건 제가 결정했으니까, 다들 이대로 진행해 주세요.", delay: 26000, triggerIntervention: "PRINCIPLE_VIOLATION" },
  { speaker: "박영희", text: "네, 알겠습니다.", delay: 34000 },
  { speaker: "김철수", text: "좋습니다. 그럼 다음 주까지 각자 태스크 정리해주세요.", delay: 38000, triggerIntervention: "PARTICIPATION_IMBALANCE" },
];

const interventionMessages: Record<string, {
  id: string;
  type: string;
  message: string;
  parkingLotItem?: string;
  violatedPrinciple?: string;
  suggestedSpeaker?: string;
}> = {
  TOPIC_DRIFT: {
    id: "int_demo_001",
    type: "TOPIC_DRIFT",
    message: "잠깐요, 아젠다에서 벗어났어요. '스프린트 계획'으로 돌아갈게요. 점심 메뉴는 Parking Lot에 추가했습니다.",
    parkingLotItem: "점심 메뉴",
  },
  PRINCIPLE_VIOLATION: {
    id: "int_demo_002",
    type: "PRINCIPLE_VIOLATION",
    message: "멈춰주세요! '수평적 의사결정' 원칙 위반입니다. 혼자 결정하시면 안 돼요. 다른 분들 동의하시나요?",
    violatedPrinciple: "수평적 의사결정",
  },
  PARTICIPATION_IMBALANCE: {
    id: "int_demo_003",
    type: "PARTICIPATION_IMBALANCE",
    message: "잠깐요! 최지은 님 아직 한 번도 발언 안 하셨어요. 디자인 관점에서 어떻게 보세요?",
    suggestedSpeaker: "최지은",
  },
};

export class DemoSimulator {
  private timeouts: NodeJS.Timeout[] = [];
  private isRunning = false;
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
    }) => void
  ) {
    this.onTranscript = onTranscript;
    this.onIntervention = onIntervention;
  }

  start() {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;

    demoScript.forEach((entry, index) => {
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
              ...interventionMessages[entry.triggerIntervention!],
              timestamp: new Date().toISOString(),
            });
          }, 1500);

          // Track the nested timeout for cleanup
          this.timeouts.push(interventionTimeout);
        }
      }, entry.delay);

      this.timeouts.push(timeout);
    });
  }

  stop() {
    this.isRunning = false;
    this.timeouts.forEach(clearTimeout);
    this.timeouts = [];
  }
}
