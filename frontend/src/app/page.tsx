"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { registry } from "@/lib/agents/registry";
import { createTranscriptStreamer, type TranscriptSegment } from "@/lib/meeting/streaming";

type DeviceLists = {
  video: MediaDeviceInfo[];
  audio: MediaDeviceInfo[];
};

const statusCopy = {
  idle: "Waiting for camera and microphone permissions.",
  active: "Devices are ready. You can join a local session.",
  muted: "Microphone muted. Others will not hear you.",
};

export default function Home() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [deviceLists, setDeviceLists] = useState<DeviceLists>({ video: [], audio: [] });
  const [selectedVideo, setSelectedVideo] = useState("");
  const [selectedAudio, setSelectedAudio] = useState("");
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isMicOn, setIsMicOn] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [roomName, setRoomName] = useState("Sprint Review");
  const [displayName, setDisplayName] = useState("Host");
  const [participants, setParticipants] = useState<string[]>(["Host"]);
  const [botEnabled, setBotEnabled] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [isStreamingDemo, setIsStreamingDemo] = useState(false);
  const streamerRef = useRef(createTranscriptStreamer());
  const demoIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [textInput, setTextInput] = useState("");
  const [textSpeaker, setTextSpeaker] = useState("Host");
  const [textRole, setTextRole] = useState<TranscriptSegment["role"]>("host");
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [joinCode, setJoinCode] = useState("");
  const [inMeeting, setInMeeting] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [isSpeechActive, setIsSpeechActive] = useState(false);
  const [speechSupport, setSpeechSupport] = useState(true);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const router = useRouter();

  const statusLabel = useMemo(() => {
    if (!stream) return statusCopy.idle;
    if (!isMicOn) return statusCopy.muted;
    return statusCopy.active;
  }, [stream, isMicOn]);

  const updateDeviceLists = useCallback(async () => {
    if (!navigator?.mediaDevices?.enumerateDevices) return;
    const devices = await navigator.mediaDevices.enumerateDevices();
    const video = devices.filter((device) => device.kind === "videoinput");
    const audio = devices.filter((device) => device.kind === "audioinput");
    setDeviceLists({ video, audio });
    if (!selectedVideo && video[0]) setSelectedVideo(video[0].deviceId);
    if (!selectedAudio && audio[0]) setSelectedAudio(audio[0].deviceId);
  }, [selectedAudio, selectedVideo]);

  const stopStream = useCallback(() => {
    if (!stream) return;
    stream.getTracks().forEach((track) => track.stop());
    setStream(null);
    setIsCameraOn(false);
    setIsMicOn(false);
    setMicLevel(0);
  }, [stream]);

  const startPreview = useCallback(async () => {
    setError(null);
    stopStream();
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: selectedVideo
          ? { deviceId: { exact: selectedVideo }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : true,
        audio: selectedAudio
          ? {
              deviceId: { exact: selectedAudio },
              echoCancellation: true,
              noiseSuppression: true,
            }
          : true,
      });

      setStream(media);
      const videoTrack = media.getVideoTracks()[0];
      const audioTrack = media.getAudioTracks()[0];
      setIsCameraOn(videoTrack ? videoTrack.enabled : false);
      setIsMicOn(audioTrack ? audioTrack.enabled : false);
      await updateDeviceLists();
    } catch (err) {
      setError("Permission denied or device unavailable. Please check browser settings.");
      stopStream();
    }
  }, [selectedVideo, selectedAudio, stopStream, updateDeviceLists]);

  const toggleCamera = useCallback(() => {
    if (!stream) return;
    const [track] = stream.getVideoTracks();
    if (!track) return;
    track.enabled = !track.enabled;
    setIsCameraOn(track.enabled);
  }, [stream]);

  const toggleMic = useCallback(() => {
    if (!stream) return;
    const [track] = stream.getAudioTracks();
    if (!track) return;
    track.enabled = !track.enabled;
    setIsMicOn(track.enabled);
  }, [stream]);

  const appendSegment = useCallback((segment: TranscriptSegment) => {
    setTranscript((prev) => {
      const index = prev.findIndex((item) => item.id === segment.id);
      if (index === -1) return [...prev, segment];
      const updated = [...prev];
      updated[index] = segment;
      return updated;
    });
  }, []);

  const saveTranscript = useCallback(() => {
    const lines = transcript.map((segment) => {
      const time = segment.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      return `[${time}] ${segment.speaker}: ${segment.text}`;
    });
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `meeting-${roomName.replace(/\s+/g, "-").toLowerCase()}-transcript.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }, [roomName, transcript]);

  const stopDemoStream = useCallback(() => {
    if (demoIntervalRef.current) {
      clearInterval(demoIntervalRef.current);
      demoIntervalRef.current = null;
    }
    setIsStreamingDemo(false);
  }, []);

  const startDemoStream = useCallback(() => {
    if (isStreamingDemo) return;
    setIsStreamingDemo(true);
    const script = [
      { speaker: displayName || "Host", role: "host", text: "Let's kick off the review with wins." },
      { speaker: "Teammate A", role: "guest", text: "Shipping velocity jumped after the infra fixes." },
      { speaker: botEnabled ? "Moderator Bot" : "Teammate B", role: botEnabled ? "bot" : "guest", text: "Let's keep to the agenda. Next: blockers." },
      { speaker: displayName || "Host", role: "host", text: "Cool, blockers: we need API rate limits." },
    ];
    let index = 0;
    demoIntervalRef.current = setInterval(() => {
      const next = script[index % script.length];
      const id = `${Date.now()}-${index}`;
      const draft: TranscriptSegment = {
        id,
        speaker: next.speaker,
        role: next.role as TranscriptSegment["role"],
        text: "",
        timestamp: new Date(),
        isFinal: false,
      };
      streamerRef.current.push(draft);
      let cursor = 0;
      const phrase = next.text;
      const typing = setInterval(() => {
        cursor += 1;
        const current: TranscriptSegment = {
          ...draft,
          text: phrase.slice(0, cursor),
          isFinal: cursor >= phrase.length,
        };
        streamerRef.current.push(current);
        if (cursor >= phrase.length) {
          clearInterval(typing);
        }
      }, 40);
      index += 1;
    }, 2400);
  }, [appendSegment, botEnabled, displayName, isStreamingDemo]);

  const toggleBot = useCallback(() => {
    setBotEnabled((prev) => !prev);
  }, []);

  const submitTextInput = useCallback(() => {
    if (!textInput.trim()) return;
    const segment: TranscriptSegment = {
      id: `${Date.now()}-manual`,
      speaker: textSpeaker || "Guest",
      role: textRole,
      text: textInput.trim(),
      timestamp: new Date(),
      isFinal: true,
    };
    streamerRef.current.push(segment);
    setTextInput("");
  }, [textInput, textRole, textSpeaker]);

  const syncUrlRoom = useCallback((room: string | null) => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (room) {
      url.searchParams.set("room", room);
    } else {
      url.searchParams.delete("room");
    }
    window.history.replaceState({}, "", url.toString());
  }, []);

  const createRoomId = useCallback(() => {
    const alphabet = "abcdefghjkmnpqrstuvwxyz23456789";
    let value = "";
    for (let i = 0; i < 6; i += 1) {
      value += alphabet[Math.floor(Math.random() * alphabet.length)];
    }
    return value;
  }, []);

  const startLocalSession = useCallback(() => {
    const id = createRoomId();
    setMeetingId(id);
    setInMeeting(true);
    setJoinCode(id);
    syncUrlRoom(id);
    router.push(`/meeting/${id}`);
  }, [createRoomId, router, syncUrlRoom]);

  const joinSession = useCallback(() => {
    if (!joinCode.trim()) return;
    const id = joinCode.trim();
    setMeetingId(id);
    setInMeeting(true);
    syncUrlRoom(id);
    router.push(`/meeting/${id}`);
  }, [joinCode, router, syncUrlRoom]);

  const leaveSession = useCallback(() => {
    setInMeeting(false);
    setMeetingId(null);
    syncUrlRoom(null);
  }, [syncUrlRoom]);

  const copyRoomLink = useCallback(async () => {
    if (!meetingId) return;
    const url = new URL(window.location.href);
    url.searchParams.set("room", meetingId);
    try {
      await navigator.clipboard.writeText(url.toString());
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 1500);
    } catch (err) {
      setCopiedLink(false);
    }
  }, [meetingId]);

  const stopSpeech = useCallback(() => {
    recognitionRef.current?.stop();
    setIsSpeechActive(false);
  }, []);

  const startSpeech = useCallback(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognitionCtor =
      (window as typeof window & { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ??
      (window as typeof window & { webkitSpeechRecognition?: typeof SpeechRecognition })
        .webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setSpeechSupport(false);
      return;
    }
    setSpeechSupport(true);
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = result[0]?.transcript?.trim();
        if (!text) continue;
        const segment: TranscriptSegment = {
          id: `speech-${Date.now()}-${i}`,
          speaker: displayName || "Host",
          role: "host",
          text,
          timestamp: new Date(),
          isFinal: result.isFinal,
        };
        streamerRef.current.push(segment);
      }
    };

    recognition.onerror = () => {
      setIsSpeechActive(false);
    };

    recognition.onend = () => {
      setIsSpeechActive(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsSpeechActive(true);
  }, [displayName]);

  const toggleSpeech = useCallback(() => {
    if (isSpeechActive) {
      stopSpeech();
    } else {
      startSpeech();
    }
  }, [isSpeechActive, startSpeech, stopSpeech]);

  useEffect(() => {
    updateDeviceLists();
    const handler = () => updateDeviceLists();
    navigator.mediaDevices?.addEventListener?.("devicechange", handler);
    return () => navigator.mediaDevices?.removeEventListener?.("devicechange", handler);
  }, [updateDeviceLists]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    const room = url.searchParams.get("room");
    if (room) {
      setJoinCode(room);
      setMeetingId(room);
      setInMeeting(true);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = streamerRef.current.onSegment(appendSegment);
    return () => unsubscribe();
  }, [appendSegment]);

  useEffect(() => {
    const updated = new Set<string>();
    if (displayName) updated.add(displayName);
    if (botEnabled) updated.add("Moderator Bot");
    transcript.forEach((segment) => updated.add(segment.speaker));
    setParticipants(Array.from(updated));
  }, [displayName, botEnabled, transcript]);

  useEffect(() => {
    if (!videoRef.current) return;
    if (stream) {
      videoRef.current.srcObject = stream;
    } else {
      videoRef.current.srcObject = null;
    }
  }, [stream]);

  useEffect(() => {
    if (!stream) return;
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    const data = new Uint8Array(analyser.fftSize);
    let animationId: number;

    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i += 1) {
        const normalized = (data[i] - 128) / 128;
        sum += normalized * normalized;
      }
      const rms = Math.sqrt(sum / data.length);
      setMicLevel(isMicOn ? Math.min(1, rms * 2.4) : 0);
      animationId = requestAnimationFrame(tick);
    };

    tick();

    return () => {
      cancelAnimationFrame(animationId);
      audioContext.close();
    };
  }, [stream, isMicOn]);

  useEffect(
    () => () => {
      stopStream();
      stopDemoStream();
      stopSpeech();
    },
    [stopStream, stopDemoStream, stopSpeech],
  );

  const canJoin = Boolean(stream && isMicOn && isCameraOn);

  return (
    <div className="min-h-screen text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-muted">MeetingMod</p>
            <h1 className="mt-3 font-[var(--font-display)] text-4xl font-semibold text-ink md:text-5xl">
              Local Meeting Studio
            </h1>
            <p className="mt-3 max-w-xl text-base text-muted md:text-lg">
              Spin up a quick room on localhost, capture camera + voice, and keep meetings on track.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              className="rounded-full border border-ink/10 bg-card px-4 py-2 text-sm font-medium text-ink shadow-[var(--shadow-soft)] transition hover:-translate-y-0.5 hover:shadow-[var(--shadow)]"
              onClick={() => window.alert("Docs coming soon.")}
              type="button"
            >
              View demo notes
            </button>
            <button
              className="rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow)] transition hover:-translate-y-0.5"
              onClick={stream ? stopStream : startPreview}
              type="button"
            >
              {stream ? "Reset devices" : "Enable camera + mic"}
            </button>
          </div>
        </header>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
          <section className="relative overflow-hidden rounded-[32px] bg-card p-6 shadow-[var(--shadow)]">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-muted">Preview</p>
                <h2 className="text-2xl font-semibold text-ink">Camera & Voice Check</h2>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    stream ? "bg-accent-2" : "bg-amber-400"
                  }`}
                />
                <p className="text-sm text-muted">{stream ? "Ready" : "Idle"}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-[2fr_1fr]">
              <div className="relative overflow-hidden rounded-3xl border border-ink/10 bg-ink">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className={`h-full w-full object-cover ${stream ? "opacity-100" : "opacity-0"}`}
                />
                {!stream && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-ink to-accent-3 text-white">
                    <div className="h-16 w-16 rounded-full border border-white/30 bg-white/10" />
                    <p className="mt-4 text-sm uppercase tracking-[0.3em] text-white/70">No feed</p>
                    <p className="mt-2 max-w-xs text-center text-lg font-semibold">
                      Allow camera access to see your live preview.
                    </p>
                  </div>
                )}
                <div className="pointer-events-none absolute bottom-4 left-4 rounded-full bg-black/50 px-4 py-1.5 text-xs text-white">
                  {displayName || "Host"}
                </div>
              </div>

              <div className="flex flex-col justify-between gap-4 rounded-3xl border border-ink/10 bg-white/60 p-4 backdrop-blur">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">Voice meter</p>
                  <div className="mt-3 h-24 rounded-2xl border border-ink/10 bg-white/70 p-3">
                    <div className="flex h-full items-end gap-2">
                      <div className="h-full w-2 rounded-full bg-ink/10" />
                      <div className="flex h-full flex-1 items-end">
                        <div
                          className="w-full rounded-full bg-accent-2 transition-all"
                          style={{ height: `${Math.max(8, micLevel * 100)}%` }}
                        />
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-muted">{isMicOn ? "Listening" : "Muted"}</p>
                  </div>
                </div>

                <div className="rounded-2xl border border-ink/10 bg-white/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                    Status
                  </p>
                  <p className="mt-2 text-sm text-ink">{statusLabel}</p>
                  {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
                </div>

                <div className="rounded-2xl border border-ink/10 bg-white/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">Quick tips</p>
                  <ul className="mt-2 space-y-2 text-xs text-muted">
                    <li>• Use headphones to prevent echo.</li>
                    <li>• Speak after the chime for interventions.</li>
                    <li>• Keep browser tab focused during demo.</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isCameraOn
                    ? "bg-ink text-white"
                    : "border border-ink/20 bg-white text-ink"
                }`}
                onClick={toggleCamera}
                type="button"
                disabled={!stream}
              >
                {isCameraOn ? "Camera on" : "Camera off"}
              </button>
              <button
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isMicOn ? "bg-accent-2 text-white" : "border border-ink/20 bg-white text-ink"
                }`}
                onClick={toggleMic}
                type="button"
                disabled={!stream}
              >
                {isMicOn ? "Mic on" : "Mic muted"}
              </button>
              <button
                className="rounded-full border border-ink/10 bg-white px-4 py-2 text-sm font-semibold text-ink"
                type="button"
                onClick={() => window.alert("Chime check ready.")}
              >
                Play chime
              </button>
            </div>

            <div className="mt-8 grid gap-4 lg:grid-cols-[2fr_1fr]">
              <div className="rounded-3xl border border-ink/10 bg-white/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                      Live transcript
                    </p>
                    <h3 className="mt-1 text-lg font-semibold text-ink">Streaming text capture</h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      className="rounded-full border border-ink/10 bg-white px-3 py-1.5 text-xs font-semibold text-ink"
                      type="button"
                      onClick={saveTranscript}
                      disabled={transcript.length === 0}
                    >
                      Save .txt
                    </button>
                    <button
                      className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                        isStreamingDemo ? "bg-accent text-white" : "border border-ink/10 bg-white text-ink"
                      }`}
                      type="button"
                      onClick={isStreamingDemo ? stopDemoStream : startDemoStream}
                    >
                      {isStreamingDemo ? "Stop stream" : "Demo stream"}
                    </button>
                  </div>
                </div>
                <div className="mt-4 max-h-56 space-y-3 overflow-y-auto pr-2 text-sm text-ink">
                  {transcript.length === 0 && (
                    <p className="text-sm text-muted">Streamed text will appear here in real time.</p>
                  )}
                  {transcript.map((segment) => (
                    <div key={segment.id} className="rounded-2xl border border-ink/10 bg-white/80 p-3">
                      <div className="flex items-center justify-between text-xs text-muted">
                        <span className="font-semibold uppercase tracking-[0.2em]">{segment.speaker}</span>
                        <span>{segment.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>
                      <p className="mt-2 text-sm text-ink">
                        {segment.text}
                        {!segment.isFinal && <span className="ml-1 animate-pulse text-muted">▌</span>}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 rounded-2xl border border-ink/10 bg-white/80 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                        Live speech (demo)
                      </p>
                      <p className="mt-1 text-sm text-muted">
                        Use browser speech recognition to stream your mic as text.
                      </p>
                      {!speechSupport && (
                        <p className="mt-2 text-xs text-red-600">
                          This browser does not support SpeechRecognition. Try Chrome.
                        </p>
                      )}
                    </div>
                    <button
                      className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                        isSpeechActive ? "bg-accent-2 text-white" : "border border-ink/10 bg-white text-ink"
                      }`}
                      type="button"
                      onClick={toggleSpeech}
                    >
                      {isSpeechActive ? "Stop live text" : "Start live text"}
                    </button>
                  </div>
                </div>
                <div className="mt-4 rounded-2xl border border-ink/10 bg-white/80 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                    Text input mode
                  </p>
                  <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr]">
                    <input
                      className="w-full rounded-2xl border border-ink/10 bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                      value={textSpeaker}
                      onChange={(event) => setTextSpeaker(event.target.value)}
                      placeholder="Speaker name"
                    />
                    <select
                      className="w-full rounded-2xl border border-ink/10 bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                      value={textRole}
                      onChange={(event) => setTextRole(event.target.value as TranscriptSegment["role"])}
                    >
                      <option value="host">Host</option>
                      <option value="guest">Guest</option>
                      <option value="bot">Bot</option>
                    </select>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <input
                      className="flex-1 rounded-2xl border border-ink/10 bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                      value={textInput}
                      onChange={(event) => setTextInput(event.target.value)}
                      placeholder="Type a message to add to the transcript..."
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          submitTextInput();
                        }
                      }}
                    />
                    <button
                      className="rounded-full bg-ink px-4 py-2 text-xs font-semibold text-white"
                      type="button"
                      onClick={submitTextInput}
                    >
                      Add
                    </button>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-ink/10 bg-white/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">Participants</p>
                <div className="mt-3 space-y-2 text-sm text-ink">
                  {participants.map((participant) => (
                    <div key={participant} className="flex items-center justify-between rounded-2xl bg-white/80 px-3 py-2">
                      <span>{participant}</span>
                      <span className="text-xs text-muted">{participant === "Moderator Bot" ? "bot" : "live"}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <aside className="flex flex-col gap-6">
            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">Room details</h3>
              <p className="mt-2 text-sm text-muted">Set the name and room title for this session.</p>
              <div className="mt-4 space-y-3">
                <label className="block text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                  Display name
                </label>
                <input
                  className="w-full rounded-2xl border border-ink/10 bg-white/70 px-4 py-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Host"
                />
                <label className="block text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                  Room title
                </label>
                <input
                  className="w-full rounded-2xl border border-ink/10 bg-white/70 px-4 py-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  value={roomName}
                  onChange={(event) => setRoomName(event.target.value)}
                  placeholder="Sprint Review"
                />
              </div>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">Device routing</h3>
              <p className="mt-2 text-sm text-muted">
                Select which camera and microphone to attach to your meeting.
              </p>
              <div className="mt-4 space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                    Camera
                  </label>
                  <select
                    className="mt-2 w-full rounded-2xl border border-ink/10 bg-white/80 px-4 py-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                    value={selectedVideo}
                    onChange={(event) => setSelectedVideo(event.target.value)}
                  >
                    {deviceLists.video.length === 0 && (
                      <option value="">No camera detected</option>
                    )}
                    {deviceLists.video.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label || `Camera ${device.deviceId.slice(0, 6)}`}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.3em] text-muted">
                    Microphone
                  </label>
                  <select
                    className="mt-2 w-full rounded-2xl border border-ink/10 bg-white/80 px-4 py-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                    value={selectedAudio}
                    onChange={(event) => setSelectedAudio(event.target.value)}
                  >
                    {deviceLists.audio.length === 0 && (
                      <option value="">No microphone detected</option>
                    )}
                    {deviceLists.audio.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label || `Mic ${device.deviceId.slice(0, 6)}`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                className="mt-4 w-full rounded-full border border-ink/10 bg-white px-4 py-2.5 text-sm font-semibold text-ink"
                type="button"
                onClick={startPreview}
              >
                Refresh devices
              </button>
            </div>

            <div className="rounded-[28px] bg-card p-6 shadow-[var(--shadow-soft)]">
              <h3 className="text-lg font-semibold text-ink">AI agents</h3>
              <p className="mt-2 text-sm text-muted">
                Drop in assistant bots that can moderate or capture notes.
              </p>
              <div className="mt-4 flex items-center justify-between rounded-2xl border border-ink/10 bg-white/70 px-4 py-3 text-sm">
                <div>
                  <p className="font-semibold text-ink">Moderator Bot</p>
                  <p className="text-xs text-muted">Gentle nudges, topic focus</p>
                </div>
                <button
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                    botEnabled ? "bg-accent-2 text-white" : "border border-ink/10 bg-white text-ink"
                  }`}
                  type="button"
                  onClick={toggleBot}
                >
                  {botEnabled ? "Remove" : "Add bot"}
                </button>
              </div>
              <div className="mt-4 space-y-2 text-xs text-muted">
                {registry.list().map((agent) => (
                  <div key={agent.id} className="rounded-2xl border border-ink/10 bg-white/70 px-3 py-2">
                    <p className="font-semibold text-ink">{agent.name}</p>
                    <p className="text-xs text-muted">{agent.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] bg-ink p-6 text-white shadow-[var(--shadow)]">
              <h3 className="text-lg font-semibold">Join a room</h3>
              <p className="mt-2 text-sm text-white/70">
                Start a localhost room or join an existing room code.
              </p>
              {inMeeting ? (
                <div className="mt-4 space-y-3">
                  <div className="rounded-2xl bg-white/10 px-4 py-3 text-sm">
                    <p className="text-xs uppercase tracking-[0.3em] text-white/60">Room</p>
                    <p className="mt-1 text-lg font-semibold">{meetingId}</p>
                  </div>
                  <button
                    className="w-full rounded-full border border-white/30 px-4 py-2.5 text-sm font-semibold text-white"
                    type="button"
                    onClick={copyRoomLink}
                  >
                    {copiedLink ? "Link copied" : "Copy invite link"}
                  </button>
                  <button
                    className="w-full rounded-full bg-white/20 px-4 py-2.5 text-sm font-semibold text-white"
                    type="button"
                    onClick={leaveSession}
                  >
                    Leave room
                  </button>
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  <button
                    className={`w-full rounded-full px-4 py-3 text-sm font-semibold transition ${
                      canJoin ? "bg-accent text-white" : "bg-white/20 text-white/70"
                    }`}
                    type="button"
                    disabled={!canJoin}
                    onClick={startLocalSession}
                  >
                    {canJoin ? "Start local session" : "Enable camera + mic first"}
                  </button>
                  <div className="rounded-2xl bg-white/10 p-3">
                    <label className="text-xs font-semibold uppercase tracking-[0.3em] text-white/60">
                      Join code
                    </label>
                    <input
                      className="mt-2 w-full rounded-2xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                      value={joinCode}
                      onChange={(event) => setJoinCode(event.target.value)}
                      placeholder="e.g. ab3k9p"
                    />
                    <button
                      className="mt-3 w-full rounded-full bg-white/20 px-4 py-2.5 text-sm font-semibold text-white"
                      type="button"
                      onClick={joinSession}
                      disabled={!joinCode.trim()}
                    >
                      Join room
                    </button>
                  </div>
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
