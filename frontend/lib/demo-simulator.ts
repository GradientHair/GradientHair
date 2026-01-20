import { soundPlayer } from "./sound-player";
import { t } from "./i18n";

export interface DemoScriptEntry {
  speaker: string;
  text: string;
  delay: number;
  triggerIntervention?: string;
}

export const demoScript: DemoScriptEntry[] = [
  { speaker: t("demo.speaker1"), text: t("demo.lines.1"), delay: 0 },
  { speaker: t("demo.speaker2"), text: t("demo.lines.2"), delay: 3000 },
  { speaker: t("demo.speaker1"), text: t("demo.lines.3"), delay: 6000 },
  { speaker: t("demo.speaker2"), text: t("demo.lines.4"), delay: 10000, triggerIntervention: "TOPIC_DRIFT" },
  { speaker: t("demo.speaker1"), text: t("demo.lines.5"), delay: 18000 },
  { speaker: t("demo.speaker1"), text: t("demo.lines.6"), delay: 22000 },
  { speaker: t("demo.speaker1"), text: t("demo.lines.7"), delay: 26000, triggerIntervention: "PRINCIPLE_VIOLATION" },
  { speaker: t("demo.speaker3"), text: t("demo.lines.8"), delay: 34000 },
  { speaker: t("demo.speaker1"), text: t("demo.lines.9"), delay: 38000, triggerIntervention: "PARTICIPATION_IMBALANCE" },
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
    message: t("demo.topicDrift"),
    parkingLotItem: t("demo.parkingLot"),
  },
  PRINCIPLE_VIOLATION: {
    id: "int_demo_002",
    type: "PRINCIPLE_VIOLATION",
    message: t("demo.principleViolation"),
    violatedPrinciple: t("demo.violatedPrinciple"),
  },
  PARTICIPATION_IMBALANCE: {
    id: "int_demo_003",
    type: "PARTICIPATION_IMBALANCE",
    message: t("demo.participation"),
    suggestedSpeaker: t("demo.speakerSuggest"),
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
