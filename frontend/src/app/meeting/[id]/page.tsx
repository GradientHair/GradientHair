"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createTranscriptStreamer, type TranscriptSegment } from "@/lib/meeting/streaming";

const botName = "Moderator Bot";
const koreanParticipants = ["김철수", "이민수", "박영희", "최지은"];

type InterventionKind = "TOPIC_DRIFT" | "PARTICIPATION_IMBALANCE" | "PRINCIPLE_VIOLATION";

const interventionMessages: Record<InterventionKind, string> = {
  TOPIC_DRIFT:
    "잠깐요, 아젠다에서 벗어났어요. '스프린트 계획'으로 돌아갈게요. 점심 메뉴는 Parking Lot에 추가했습니다.",
  PARTICIPATION_IMBALANCE:
    "잠깐요! 박영희 님 아직 발언 안 하셨어요. 백엔드 관점에서 이 기능 어떻게 보세요?",
  PRINCIPLE_VIOLATION:
    "멈춰주세요! '수평적 의사결정' 원칙 위반입니다. 혼자 결정하시면 안 돼요. 다른 분들, 동의하시나요?",
};

export default function MeetingRoom() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [textInput, setTextInput] = useState("");
  const [displayName, setDisplayName] = useState("김철수");
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastVisible, setToastVisible] = useState(false);
  const [stats, setStats] = useState<Record<string, number>>({
    김철수: 45,
    이민수: 35,
    박영희: 12,
    최지은: 8,
  });
  const streamerRef = useRef(createTranscriptStreamer());
  const demoIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const roomId = params?.id ?? "local";

  const participants = useMemo(() => {
    const set = new Set<string>([displayName, botName, ...koreanParticipants]);
    transcript.forEach((segment) => set.add(segment.speaker));
    return Array.from(set);
  }, [displayName, transcript]);

  const appendSegment = useCallback((segment: TranscriptSegment) => {
    setTranscript((prev) => {
      const index = prev.findIndex((item) => item.id === segment.id);
      if (index === -1) return [...prev, segment];
      const updated = [...prev];
      updated[index] = segment;
      return updated;
    });
  }, []);

  const startDemo = useCallback(() => {
    if (isDemoRunning) return;
    setIsDemoRunning(true);
    const script = [
      { speaker: "김철수", role: "host" as const, text: "지난 스프린트에서 8개 태스크를 완료했습니다." },
      { speaker: "이민수", role: "guest" as const, text: "네, 성과가 좋았어요. 특히 로그인 개선이 효과적이었습니다." },
      { speaker: "김철수", role: "host" as const, text: "다음 스프린트에서는 온보딩 플로우를 개선하려고 합니다." },
      {
        speaker: "이민수",
        role: "guest" as const,
        text: "그런데 점심 뭐 먹을까요? 회사 앞에 새로 생긴 라멘집이 맛있다던데...",
      },
    ];
    let index = 0;
    demoIntervalRef.current = setInterval(() => {
      const next = script[index % script.length];
      const id = `${Date.now()}-${index}`;
      const draft: TranscriptSegment = {
        id,
        speaker: next.speaker,
        role: next.role,
        text: "",
        timestamp: new Date(),
        isFinal: false,
      };
      streamerRef.current.push(draft);
      let cursor = 0;
      const typing = setInterval(() => {
        cursor += 1;
        streamerRef.current.push({
          ...draft,
          text: next.text.slice(0, cursor),
          isFinal: cursor >= next.text.length,
        });
        if (cursor >= next.text.length) {
          clearInterval(typing);
        }
      }, 40);
      index += 1;
      if (index === 4) {
        setTimeout(() => triggerIntervention("TOPIC_DRIFT"), 1400);
      }
    }, 2300);
  }, [displayName, isDemoRunning]);

  const stopDemo = useCallback(() => {
    if (demoIntervalRef.current) {
      clearInterval(demoIntervalRef.current);
      demoIntervalRef.current = null;
    }
    setIsDemoRunning(false);
  }, []);

  const submitText = useCallback(() => {
    if (!textInput.trim()) return;
    const segment: TranscriptSegment = {
      id: `${Date.now()}-manual`,
      speaker: displayName || "Host",
      role: "host",
      text: textInput.trim(),
      timestamp: new Date(),
      isFinal: true,
    };
    streamerRef.current.push(segment);
    setTextInput("");

    setTimeout(() => {
      streamerRef.current.push({
        id: `${Date.now()}-bot`,
        speaker: botName,
        role: "bot",
        text: "좋아요. 다음 발언자는 1분 안에 핵심만 공유해 주세요.",
        timestamp: new Date(),
        isFinal: true,
      });
    }, 800);
  }, [displayName, textInput]);

  const playChime = useCallback(() => {
    try {
      const audio = new AudioContext();
      const oscillator = audio.createOscillator();
      const gain = audio.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = 880;
      gain.gain.value = 0.08;
      oscillator.connect(gain);
      gain.connect(audio.destination);
      oscillator.start();
      gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.9);
      oscillator.stop(audio.currentTime + 1);
      oscillator.onended = () => audio.close();
    } catch (err) {
      // no-op for unsupported contexts
    }
  }, []);

  const triggerIntervention = useCallback((kind: InterventionKind) => {
    const message = interventionMessages[kind];
    setToastMessage(message);
    setToastVisible(true);
    playChime();
    setTimeout(() => setToastVisible(false), 4500);
  }, [playChime]);

  const bumpParticipationStats = useCallback(() => {
    setStats({
      김철수: 45,
      이민수: 35,
      박영희: 12,
      최지은: 8,
    });
    triggerIntervention("PARTICIPATION_IMBALANCE");
  }, [triggerIntervention]);

  const triggerPrincipleViolation = useCallback(() => {
    streamerRef.current.push({
      id: `${Date.now()}-principle`,
      speaker: "김철수",
      role: "host",
      text: "이건 제가 결정했으니까, 다들 이대로 진행해 주세요.",
      timestamp: new Date(),
      isFinal: true,
    });
    setTimeout(() => triggerIntervention("PRINCIPLE_VIOLATION"), 1200);
  }, [triggerIntervention]);

  useEffect(() => {
    const unsubscribe = streamerRef.current.onSegment(appendSegment);
    return () => unsubscribe();
  }, [appendSegment]);

  useEffect(
    () => () => {
      stopDemo();
    },
    [stopDemo],
  );

  return (
    <div className="min-h-screen text-ink">
      {toastVisible && toastMessage && (
        <div className="fixed right-6 top-6 z-50 max-w-sm rounded-2xl border border-accent/40 bg-white/95 p-4 text-sm text-ink shadow-[var(--shadow)]">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.3em] text-accent">
            🤖 Agent Intervention
          </div>
          <p className="mt-2 text-sm text-ink">{toastMessage}</p>
          <div className="mt-3 flex justify-end">
            <button
              className="rounded-full border border-ink/10 bg-white px-3 py-1 text-xs font-semibold text-ink"
              type="button"
              onClick={() => setToastVisible(false)}
            >
              무시
            </button>
          </div>
        </div>
      )}
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-muted">Meeting room</p>
            <h1 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-ink md:text-4xl">
              Room {roomId}
            </h1>
            <p className="mt-2 text-sm text-muted">
              실시간 회의 개입 데모 · 멀티 에이전트 협업 흐름 시연
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-ink/10 bg-white px-4 py-2 text-sm font-semibold text-ink"
              type="button"
              onClick={() => router.push("/")}
            >
              Back to lobby
            </button>
            <button
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                isDemoRunning ? "bg-accent text-white" : "border border-ink/10 bg-white text-ink"
              }`}
              type="button"
              onClick={isDemoRunning ? stopDemo : startDemo}
            >
              {isDemoRunning ? "데모 중지" : "데모 시작"}
            </button>
          </div>
        </header>

        <div className="mt-8 grid gap-6 lg:grid-cols-[2fr_1fr]">
          <section className="rounded-[32px] bg-card p-6 shadow-[var(--shadow)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">Live transcript</p>
                <h2 className="mt-2 text-2xl font-semibold text-ink">실시간 자막</h2>
              </div>
              <div className="rounded-full border border-ink/10 bg-white px-3 py-1 text-xs text-muted">
                실시간 텍스트 스트리밍
              </div>
            </div>

            <div className="mt-4 max-h-[420px] space-y-3 overflow-y-auto pr-2">
              {transcript.length === 0 && (
                <p className="text-sm text-muted">아직 발화가 없습니다. 데모를 시작하세요.</p>
              )}
              {transcript.map((segment) => (
                <div
                  key={segment.id}
                  className={`rounded-2xl border px-4 py-3 text-sm ${
                    segment.role === "bot"
                      ? "border-accent/40 bg-accent/10 text-ink"
                      : "border-ink/10 bg-white/80 text-ink"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs text-muted">
                    <span className="font-semibold uppercase tracking-[0.2em]">{segment.speaker}</span>
                    <span>
                      {segment.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <p className="mt-2">
                    {segment.text}
                    {!segment.isFinal && <span className="ml-1 animate-pulse text-muted">▌</span>}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-2xl border border-ink/10 bg-white/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                참석자 발화 입력
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr]">
                <input
                  className="w-full rounded-2xl border border-ink/10 bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="참석자 이름"
                />
                <input
                  className="w-full rounded-2xl border border-ink/10 bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  value={textInput}
                  onChange={(event) => setTextInput(event.target.value)}
                  placeholder="발화 내용을 입력하세요"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      submitText();
                    }
                  }}
                />
              </div>
              <button
                className="mt-3 rounded-full bg-ink px-4 py-2 text-xs font-semibold text-white"
                type="button"
                onClick={submitText}
              >
                발화 추가
              </button>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">회의 원칙</h3>
              <p className="mt-2 text-sm text-muted">Agile 원칙 적용 중</p>
              <ul className="mt-3 space-y-2 text-xs text-muted">
                <li>• 수평적 의사결정</li>
                <li>• 타임박스 준수</li>
                <li>• Action-oriented</li>
                <li>• 짧고 집중</li>
              </ul>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">아젠다</h3>
              <p className="mt-2 text-sm text-muted">Sprint Review</p>
              <ol className="mt-3 space-y-2 text-xs text-muted">
                <li>1. 지난 스프린트 요약</li>
                <li>2. 주요 성과 공유</li>
                <li>3. 다음 스프린트 계획</li>
                <li>4. 블로커/리스크 논의</li>
              </ol>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">Participants</h3>
              <p className="mt-2 text-sm text-muted">현재 참석자와 Bot 상태</p>
              <div className="mt-4 space-y-2 text-sm">
                {participants.map((participant) => (
                  <div
                    key={participant}
                    className="flex items-center justify-between rounded-2xl border border-ink/10 bg-white/80 px-3 py-2"
                  >
                    <span>{participant}</span>
                    <span className="text-xs text-muted">
                      {participant === botName ? "bot" : "live"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">발언 통계</h3>
              <p className="mt-2 text-sm text-muted">참여 불균형 감지용 데모 데이터</p>
              <div className="mt-4 space-y-3 text-sm">
                {Object.entries(stats).map(([name, value]) => (
                  <div key={name}>
                    <div className="flex items-center justify-between text-xs text-muted">
                      <span>{name}</span>
                      <span>{value}%</span>
                    </div>
                    <div className="mt-2 h-2 w-full rounded-full bg-ink/10">
                      <div
                        className={`h-full rounded-full ${value < 10 ? "bg-amber-400" : "bg-accent-2"}`}
                        style={{ width: `${value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <button
                className="mt-4 w-full rounded-full border border-ink/10 bg-white px-4 py-2 text-xs font-semibold text-ink"
                type="button"
                onClick={bumpParticipationStats}
              >
                참여 불균형 데모
              </button>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">시뮬레이션 트리거</h3>
              <p className="mt-2 text-sm text-muted">데모 중 개입 장면을 바로 호출</p>
              <div className="mt-4 grid gap-2">
                <button
                  className="rounded-full border border-ink/10 bg-white px-4 py-2 text-xs font-semibold text-ink"
                  type="button"
                  onClick={() => triggerIntervention("TOPIC_DRIFT")}
                >
                  주제 이탈 감지
                </button>
                <button
                  className="rounded-full border border-ink/10 bg-white px-4 py-2 text-xs font-semibold text-ink"
                  type="button"
                  onClick={triggerPrincipleViolation}
                >
                  원칙 위반 감지
                </button>
              </div>
            </div>

            <div className="rounded-[28px] bg-ink p-6 text-white shadow-[var(--shadow)]">
              <h3 className="text-lg font-semibold">Bot status</h3>
              <p className="mt-2 text-sm text-white/70">
                Bot이 주제 이탈, 참여 불균형, 원칙 위반을 감지합니다.
              </p>
              <div className="mt-4 rounded-2xl bg-white/10 px-4 py-3 text-sm">
                <p className="text-xs uppercase tracking-[0.3em] text-white/60">Active</p>
                <p className="mt-1 font-semibold">실시간 자막 모니터링</p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
