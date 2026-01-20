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
  interventions: Intervention[];
  speakerStats: SpeakerStats;
  currentIntervention: Intervention | null;

  // Actions
  setTitle: (title: string) => void;
  setAgenda: (agenda: string) => void;
  addParticipant: (participant: Participant) => void;
  removeParticipant: (id: string) => void;
  setSelectedPrinciples: (principles: string[]) => void;
  startMeeting: (meetingId: string) => void;
  addTranscript: (entry: TranscriptEntry) => void;
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
  interventions: [],
  speakerStats: {},
  currentIntervention: null,

  setTitle: (title) => set({ title }),
  setAgenda: (agenda) => set({ agenda }),
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
      interventions: [],
      speakerStats: {},
      currentIntervention: null,
    }),
}));
