"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMeetingStore } from "@/store/meeting-store";
import { TranscriptView } from "@/components/transcript-view";
import { SpeakerStats } from "@/components/speaker-stats";
import { InterventionToast } from "@/components/intervention-toast";
import { useWebSocket } from "@/hooks/use-websocket";
import { useAudioCapture } from "@/hooks/use-audio-capture";
import { DemoSimulator } from "@/lib/demo-simulator";
import { getApiBase } from "@/lib/api";

export default function MeetingRoomPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = params.id as string;
  const apiBase = getApiBase();

  const { status, title, startMeeting, endMeeting, agenda, addTranscript, addIntervention, updateSpeakerStats, participants, transcript } = useMeetingStore();
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const demoRef = useRef<DemoSimulator | null>(null);
  const initializedRef = useRef(false);

  const { connect, disconnect, isConnected, sendAudio } = useWebSocket(meetingId);
  const { start, stop, pause, resume, isRecording } = useAudioCapture(sendAudio);

  // Initialize meeting - only run once
  useEffect(() => {
    if (initializedRef.current) {
      return;
    }
    initializedRef.current = true;

    console.log("Initializing meeting:", meetingId);
    startMeeting(meetingId);

    // Connect to backend WebSocket
    connect();

    // Start audio capture
    start().catch((error) => {
      console.log("Audio capture not available:", error);
    });

    // Timer for elapsed time
    const timer = setInterval(() => {
      setElapsedTime((t) => t + 1);
    }, 1000);

    return () => {
      console.log("Cleaning up meeting:", meetingId);
      clearInterval(timer);
      stop();
      disconnect();
      demoRef.current?.stop();
      initializedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId]);

  // Update speaker stats in demo mode
  useEffect(() => {
    if (isDemoMode && participants.length > 0) {
      const speakerCounts: Record<string, number> = {};
      transcript.forEach((t) => {
        speakerCounts[t.speaker] = (speakerCounts[t.speaker] || 0) + 1;
      });

      const total = Object.values(speakerCounts).reduce((a, b) => a + b, 0);
      if (total > 0) {
        const stats: Record<string, { percentage: number; speakingTime: number; count: number }> = {};
        participants.forEach((p) => {
          const count = speakerCounts[p.name] || 0;
          stats[p.name] = {
            percentage: Math.round((count / total) * 100),
            speakingTime: count * 5,
            count,
          };
        });
        updateSpeakerStats(stats);
      }
    }
  }, [isDemoMode, transcript, participants, updateSpeakerStats]);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleMuteToggle = async () => {
    if (!isRecording) {
      try {
        await start();
        setIsMuted(false);
        return;
      } catch (error) {
        console.error("Audio capture not available:", error);
        return;
      }
    }

    if (isMuted) {
      resume();
    } else {
      pause();
    }
    setIsMuted(!isMuted);
  };

  const startDemoMode = () => {
    setIsDemoMode(true);
    demoRef.current = new DemoSimulator(
      (entry) => addTranscript(entry),
      (intervention) => addIntervention(intervention as Parameters<typeof addIntervention>[0]),
      {
        agenda,
        participants: participants.map((p) => ({ name: p.name, role: p.role })),
        persona: "직설적이고 빠른 의사결정, 때때로 공격적으로 들릴 수 있음",
        useLLM: true,
      }
    );
    demoRef.current.start();
  };

  const stopDemoMode = () => {
    setIsDemoMode(false);
    demoRef.current?.stop();
  };

  const handleEndMeeting = async () => {
    stop();
    demoRef.current?.stop();

    // 현재 상태 가져오기
    const state = useMeetingStore.getState();

    try {
      // 데모 모드 또는 오프라인: 프론트엔드 데이터를 백엔드로 전송하여 저장
      const response = await fetch(`${apiBase}/meetings/${meetingId}/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: state.title || meetingId,
          agenda: state.agenda,
          participants: state.participants,
          transcript: state.transcript,
          interventions: state.interventions,
          speakerStats: state.speakerStats,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Meeting saved:", result);
      }
    } catch (error) {
      console.error("Failed to save meeting:", error);
    }

    endMeeting();
    router.push(`/review/${meetingId}`);
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">{title || meetingId}</h2>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              REC
            </span>
            <span>{formatTime(elapsedTime)}</span>
            <span className={isConnected ? "text-green-600" : isDemoMode ? "text-blue-600" : "text-yellow-600"}>
              {isConnected ? "연결됨" : isDemoMode ? "데모 모드" : "오프라인"}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 메인: 실시간 자막 */}
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>실시간 자막</CardTitle>
            </CardHeader>
            <CardContent>
              <TranscriptView />
            </CardContent>
          </Card>
        </div>

        {/* 사이드바 */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>발언 통계</CardTitle>
            </CardHeader>
            <CardContent>
              <SpeakerStats />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>현재 아젠다</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm whitespace-pre-wrap">{agenda || "아젠다가 설정되지 않았습니다."}</div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 컨트롤 버튼 */}
      <div className="flex justify-center gap-4 mt-6">
        <Button variant="outline" onClick={handleMuteToggle}>
          {!isRecording ? "오디오 시작" : isMuted ? "음소거 해제" : "음소거"}
        </Button>
        <Button
          variant={isDemoMode ? "destructive" : "outline"}
          onClick={isDemoMode ? stopDemoMode : startDemoMode}
        >
          {isDemoMode ? "데모 중지" : "데모 모드"}
        </Button>
        <Button variant="destructive" onClick={handleEndMeeting}>
          회의 종료
        </Button>
      </div>

      {/* 개입 Toast */}
      <InterventionToast />
    </div>
  );
}
