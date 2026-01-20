"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getApiBase } from "@/lib/api";

type MeetingFiles = {
  id: string;
  preparation?: string | null;
  transcript?: string | null;
  interventions?: string | null;
};

type ParsedPreparation = {
  title: string;
  scheduledAt: string;
  participants: Array<{ name: string; role: string }>;
  agenda: string;
};

type ParsedIntervention = {
  id: string;
  type: string;
  message: string;
};

const extractPreparation = (content?: string | null): ParsedPreparation => {
  if (!content) {
    return { title: "", scheduledAt: "", participants: [], agenda: "" };
  }

  let title = "";
  let scheduledAt = "";
  const participants: Array<{ name: string; role: string }> = [];
  let inParticipants = false;
  let inAgenda = false;
  const agendaLines: string[] = [];

  for (const rawLine of content.split("\n")) {
    const line = rawLine.trim();
    if (line.startsWith("- **제목**:")) {
      title = line.split(":", 2)[1]?.trim() ?? "";
      continue;
    }
    if (line.startsWith("- **일시**:")) {
      scheduledAt = line.split(":", 2)[1]?.trim() ?? "";
      continue;
    }
    if (line.startsWith("## 참석자")) {
      inParticipants = true;
      inAgenda = false;
      continue;
    }
    if (line.startsWith("## 아젠다")) {
      inAgenda = true;
      inParticipants = false;
      continue;
    }
    if (line.startsWith("## ")) {
      inParticipants = false;
      inAgenda = false;
      continue;
    }

    if (inParticipants && line.startsWith("|") && !line.includes("---")) {
      const cells = line.split("|").map((cell) => cell.trim()).filter(Boolean);
      if (cells.length >= 2 && cells[0] !== "이름") {
        participants.push({ name: cells[0], role: cells[1] ?? "" });
      }
    }

    if (inAgenda && line.length > 0) {
      agendaLines.push(rawLine);
    }
  }

  return {
    title,
    scheduledAt,
    participants,
    agenda: agendaLines.join("\n").trim(),
  };
};

const parseTranscriptCount = (content?: string | null) => {
  if (!content) return 0;
  return content
    .split("\n")
    .filter((line) => line.trim().startsWith("[") && line.includes("]:"))
    .length;
};

const parseInterventions = (content?: string | null): ParsedIntervention[] => {
  if (!content) return [];
  const sections = content.split("## ").slice(1);
  const parsed: ParsedIntervention[] = [];
  sections.forEach((section, index) => {
    const lines = section.split("\n").map((line) => line.trim());
    const typeLine = lines.find((line) => line.startsWith("- **유형**:"));
    const messageLine = lines.find((line) => line.startsWith("- **메시지**:"));
    parsed.push({
      id: `inv_${index}`,
      type: typeLine ? typeLine.split(":", 2)[1]?.trim() ?? "" : "INFO",
      message: messageLine ? messageLine.split(":", 2)[1]?.trim() ?? "" : "",
    });
  });
  return parsed.filter((inv) => inv.message.length > 0);
};

const formatMeetingDate = (value?: string | null) => {
  if (!value) return "날짜 정보 없음";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function MeetingHistoryDetailPage() {
  const params = useParams();
  const meetingId = params.id as string;
  const apiBase = getApiBase();
  const [meeting, setMeeting] = useState<MeetingFiles | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${apiBase}/meetings/${meetingId}/files`);
        if (!response.ok) {
          throw new Error("Failed to load meeting");
        }
        const data = await response.json();
        if (isMounted) {
          setMeeting(data);
        }
      } catch {
        if (isMounted) {
          setError("회의 상세 정보를 불러오지 못했어요.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, [meetingId]);

  const preparation = useMemo(
    () => extractPreparation(meeting?.preparation),
    [meeting?.preparation]
  );
  const transcriptCount = useMemo(
    () => parseTranscriptCount(meeting?.transcript),
    [meeting?.transcript]
  );
  const interventions = useMemo(
    () => parseInterventions(meeting?.interventions),
    [meeting?.interventions]
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card className="border-0 bg-gradient-to-br from-slate-50 via-white to-emerald-50 shadow-sm">
        <CardHeader className="space-y-2">
          <CardTitle className="text-2xl">
            {preparation.title || meeting?.id || "지난 회의"}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {formatMeetingDate(preparation.scheduledAt)}
          </p>
          <p className="text-xs text-muted-foreground">meetings/{meetingId}</p>
        </CardHeader>
      </Card>

      {loading && (
        <Card className="border-none bg-muted/30 shadow-none">
          <CardContent className="py-6 text-sm text-muted-foreground">
            불러오는 중...
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-none bg-muted/30 shadow-none">
          <CardContent className="py-6 text-sm text-red-500">{error}</CardContent>
        </Card>
      )}

      {!loading && !error && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>회의 요약</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p>
                  <strong>회의:</strong> {preparation.title || meetingId}
                </p>
                <p>
                  <strong>참석자:</strong>{" "}
                  {preparation.participants.map((p) => p.name).join(", ") || "없음"}
                </p>
                <p>
                  <strong>발화 수:</strong> {transcriptCount}
                </p>
                <p>
                  <strong>Agent 개입:</strong> {interventions.length}회
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>참여도 분포</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {preparation.participants.length === 0 && (
                  <p className="text-gray-500 text-sm">참석자 정보 없음</p>
                )}
                {preparation.participants.map((p, index) => (
                  <div key={`${p.name}-${index}`} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{p.name}</span>
                      <span>0%</span>
                    </div>
                    <Progress value={0} />
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Agent 개입 기록</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {interventions.length === 0 && (
                    <p className="text-gray-500">개입 없음</p>
                  )}
                  {interventions.map((inv) => (
                    <div key={inv.id} className="p-2 bg-gray-50 rounded">
                      <span className="font-semibold">[{inv.type}]</span>{" "}
                      {inv.message}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>저장된 파일</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-1">
                <li>preparation.md - 회의 준비 자료</li>
                <li>transcript.md - 전체 녹취록</li>
                <li>interventions.md - Agent 개입 기록</li>
                <li>summary.md - 회의 요약</li>
                <li>action-items.md - Action Items</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="flex justify-center">
        <Button asChild>
          <Link href="/">새 회의 시작</Link>
        </Button>
      </div>
    </div>
  );
}
