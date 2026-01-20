import { create } from "zustand";

interface Participant {
  id: string;
  name: string;
  role: string;
}

interface TranscriptEntry {
  id: string;
  timestamp: string;
  speaker: string;
  text: string;
  latencyMs?: number;
}

interface TranscriptStream {
  timestamp: string;
  speaker: string;
  text: string;
}

interface Intervention {
  id: string;
  type: "TOPIC_DRIFT" | "PRINCIPLE_VIOLATION" | "PARTICIPATION_IMBALANCE" | "DECISION_STYLE";
  message: string;
  timestamp: string;
  violatedPrinciple?: string;
  parkingLotItem?: string;
}

interface SpeakerStats {
  [name: string]: {
    percentage: number;
    speakingTime: number;
    count: number;
  };
}

interface MeetingState {
  // 회의 정보
  meetingId: string | null;
  title: string;
  status: "preparing" | "in_progress" | "completed";

  // 준비 단계
  agenda: string;
  participants: Participant[];
  selectedPrinciples: string[];

  // 진행 단계
  transcript: TranscriptEntry[];
  transcriptStream: TranscriptStream | null;
  interventions: Intervention[];
  speakerStats: SpeakerStats;
  currentIntervention: Intervention | null;

  // Actions
  setTitle: (title: string) => void;
  setAgenda: (agenda: string) => void;
  setParticipants: (participants: Participant[]) => void;
  addParticipant: (participant: Participant) => void;
  removeParticipant: (id: string) => void;
  setSelectedPrinciples: (principles: string[]) => void;
  startMeeting: (meetingId: string) => void;
  addTranscript: (entry: TranscriptEntry) => void;
  updateTranscriptStream: (chunk: { timestamp: string; speaker: string; text: string }) => void;
  addIntervention: (intervention: Intervention) => void;
  dismissIntervention: () => void;
  updateSpeakerStats: (stats: SpeakerStats) => void;
  endMeeting: () => void;
  reset: () => void;
}

export const useMeetingStore = create<MeetingState>((set) => ({
  meetingId: null,
  title: "",
  status: "preparing",
  agenda: "",
  participants: [],
  selectedPrinciples: ["agile"],
  transcript: [],
  transcriptStream: null,
  interventions: [],
  speakerStats: {},
  currentIntervention: null,

  setTitle: (title) => set({ title }),
  setAgenda: (agenda) => set({ agenda }),
  setParticipants: (participants) => set({ participants }),
  addParticipant: (participant) =>
    set((state) => ({ participants: [...state.participants, participant] })),
  removeParticipant: (id) =>
    set((state) => ({
      participants: state.participants.filter((p) => p.id !== id),
    })),
  setSelectedPrinciples: (principles) => set({ selectedPrinciples: principles }),
  startMeeting: (meetingId) => set({ meetingId, status: "in_progress" }),
  addTranscript: (entry) =>
    set((state) => ({ transcript: [...state.transcript, entry] })),
  updateTranscriptStream: (chunk) =>
    set((state) => {
      if (
        state.transcriptStream &&
        state.transcriptStream.timestamp === chunk.timestamp &&
        state.transcriptStream.speaker === chunk.speaker
      ) {
        return {
          transcriptStream: {
            ...state.transcriptStream,
            text: state.transcriptStream.text + chunk.text,
          },
        };
      }
      return {
        transcriptStream: {
          timestamp: chunk.timestamp,
          speaker: chunk.speaker,
          text: chunk.text,
        },
      };
    }),
  addIntervention: (intervention) =>
    set((state) => ({
      interventions: [...state.interventions, intervention],
      currentIntervention: intervention,
    })),
  dismissIntervention: () => set({ currentIntervention: null }),
  updateSpeakerStats: (stats) => set({ speakerStats: stats }),
  endMeeting: () => set({ status: "completed" }),
  reset: () =>
    set({
      meetingId: null,
      title: "",
      status: "preparing",
      agenda: "",
      participants: [],
      selectedPrinciples: ["agile"],
    transcript: [],
    transcriptStream: null,
    interventions: [],
    speakerStats: {},
    currentIntervention: null,
  }),
}));
