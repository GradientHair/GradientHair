"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMeetingStore } from "@/store/meeting-store";

export default function MeetingPrepPage() {
  const router = useRouter();
  const {
    title,
    setTitle,
    agenda,
    setAgenda,
    participants,
    setParticipants,
    addParticipant,
    removeParticipant,
    selectedPrinciples,
    setSelectedPrinciples,
  } = useMeetingStore();

  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [pasteModalOpen, setPasteModalOpen] = useState(false);
  const [pastedText, setPastedText] = useState("");
  const [principles, setPrinciples] = useState<Array<{ id: string; name: string }>>([
    { id: "agile", name: "Agile 원칙" },
    { id: "aws-leadership", name: "AWS Leadership Principles" },
  ]);

  useEffect(() => {
    let isMounted = true;
    const loadPrinciples = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/principles`);
        if (!response.ok) return;
        const data = await response.json();
        if (!Array.isArray(data.principles)) return;
        if (isMounted) {
          setPrinciples(
            data.principles.map((principle: { id: string; name: string }) => ({
              id: principle.id,
              name: principle.name,
            }))
          );
        }
      } catch {
        // fallback to defaults
      }
    };
    loadPrinciples();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleAddParticipant = () => {
    if (newName && newRole) {
      addParticipant({
        id: crypto.randomUUID(),
        name: newName,
        role: newRole,
      });
      setNewName("");
      setNewRole("");
    }
  };

  const handleStartMeeting = async () => {
    const meetingId = `${new Date().toISOString().split("T")[0]}-${title.toLowerCase().replace(/\s+/g, "-")}`;

    // API 호출하여 회의 생성
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/meetings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          agenda,
          participants,
          principleIds: selectedPrinciples,
        }),
      });

      if (response.ok) {
        router.push(`/meeting/${meetingId}`);
      }
    } catch {
      // 데모 모드에서 백엔드 없이도 동작
      router.push(`/meeting/${meetingId}`);
    }
  };

  const togglePrinciple = (id: string) => {
    if (selectedPrinciples.includes(id)) {
      setSelectedPrinciples(selectedPrinciples.filter((p) => p !== id));
    } else {
      setSelectedPrinciples([...selectedPrinciples, id]);
    }
  };

  const parseCalendarPaste = (text: string) => {
    const lines = text
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (lines.length === 0) {
      return null;
    }

    const titleLine = lines[0];
    const agendaLines: string[] = [];
    const parsedParticipants: { id: string; name: string; role: string }[] = [];
    const participantKeys = new Set<string>();
    const roleKeywords = new Set([
      "주최자",
      "참석자",
      "필수 참석자",
      "선택 참석자",
      "Organizer",
      "Host",
    ]);
    const statusKeywords = new Set(["한가함", "바쁨", "미정"]);
    const ignoreAgendaKeywords = [
      "참석자",
      "초대",
      "회신",
      "수락",
    ];

    const isDateLine = (line: string) =>
      /(\bAM\b|\bPM\b|\d{1,2}:\d{2}|월|일|\bJan\b|\bFeb\b|\bMar\b|\bApr\b|\bMay\b|\bJun\b|\bJul\b|\bAug\b|\bSep\b|\bOct\b|\bNov\b|\bDec\b)/i.test(
        line
      );

    const isLikelyName = (line: string) => {
      if (line.includes("안녕하세요")) return false;
      if (line.includes("@")) return false;
      if (/[0-9]/.test(line)) return false;
      if (line.includes("명")) return false;
      if (line.includes("초대") || line.includes("회신") || line.includes("수락")) return false;
      if (line.length > 40) return false;
      return /[A-Za-z가-힣]/.test(line);
    };

    let agendaStarted = false;
    for (let i = 1; i < lines.length; i += 1) {
      const line = lines[i];
      const nextLine = lines[i + 1];

      if (isDateLine(line)) {
        continue;
      }

      if (roleKeywords.has(line)) {
        const last = parsedParticipants[parsedParticipants.length - 1];
        if (last) {
          last.role = "";
        }
        continue;
      }

      if (statusKeywords.has(line)) {
        continue;
      }

      if (line.includes("@")) {
        if (!agendaStarted) {
          const key = line.toLowerCase();
          if (!participantKeys.has(key)) {
            participantKeys.add(key);
            parsedParticipants.push({
              id: crypto.randomUUID(),
              name: line,
              role: "",
            });
          }
        }
        continue;
      }

      if (isLikelyName(line)) {
        let role = "";
        if (nextLine && roleKeywords.has(nextLine)) {
          role = "";
          i += 1;
        }
        const cleanedName = line.replace(/\([^)]*\)/g, "").trim();
        if (!agendaStarted && cleanedName.length > 0) {
          const key = cleanedName.toLowerCase();
          if (!participantKeys.has(key)) {
            participantKeys.add(key);
            parsedParticipants.push({
              id: crypto.randomUUID(),
              name: cleanedName,
              role,
            });
          }
        }
        continue;
      }

      if (ignoreAgendaKeywords.some((keyword) => line.includes(keyword))) {
        continue;
      }

      agendaLines.push(line);
      agendaStarted = true;
    }

    return {
      title: titleLine,
      agenda: agendaLines.join("\n"),
      participants: parsedParticipants,
    };
  };

  const handlePasteSubmit = () => {
    const parsed = parseCalendarPaste(pastedText);
    if (!parsed) {
      return;
    }

    if (parsed.title) {
      setTitle(parsed.title);
    }

    if (parsed.agenda) {
      setAgenda(parsed.agenda);
    }

    if (parsed.participants.length > 0) {
      setParticipants(parsed.participants);
    }

    setPastedText("");
    setPasteModalOpen(false);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-end">
        <Dialog open={pasteModalOpen} onOpenChange={setPasteModalOpen}>
          <DialogTrigger asChild>
            <Button variant="outline">회의 붙여넣기</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>회의 붙여넣기</DialogTitle>
              <DialogDescription>
                Google Calendar에서 복사한 내용을 그대로 붙여넣으면 자동으로 입력해요.
              </DialogDescription>
            </DialogHeader>
            <Textarea
              placeholder="예: 챗봇 화면 기획 논의&#10;1월 20일 (화요일)⋅AM 10:00~ 10:30&#10;참석자 2명"
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              rows={10}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setPasteModalOpen(false)}>
                취소
              </Button>
              <Button onClick={handlePasteSubmit} disabled={!pastedText.trim()}>
                입력하기
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>회의 제목</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            placeholder="예: 주간 스프린트 리뷰"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>참석자</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="이름"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <Input
                placeholder="역할"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
              />
              <Button onClick={handleAddParticipant}>추가</Button>
            </div>
            <div className="space-y-2">
              {participants.map((p) => (
                <div key={p.id} className="flex items-center justify-between bg-gray-100 p-2 rounded">
                  <span>{p.role ? `${p.name} (${p.role})` : p.name}</span>
                  <Button variant="ghost" size="sm" onClick={() => removeParticipant(p.id)}>
                    X
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>적용할 회의 원칙</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {principles.map((p) => (
              <div
                key={p.id}
                className={`p-3 rounded border cursor-pointer ${
                  selectedPrinciples.includes(p.id)
                    ? "bg-blue-50 border-blue-500"
                    : "bg-white"
                }`}
                onClick={() => togglePrinciple(p.id)}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedPrinciples.includes(p.id)}
                    readOnly
                  />
                  <span>{p.name}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>아젠다 & 참고 자료</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="## 오늘의 아젠다&#10;&#10;1. 지난 스프린트 회고&#10;2. 다음 스프린트 계획"
            value={agenda}
            onChange={(e) => setAgenda(e.target.value)}
            rows={10}
          />
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button
          size="lg"
          onClick={handleStartMeeting}
          disabled={!title || participants.length === 0}
        >
          회의 시작
        </Button>
      </div>
    </div>
  );
}
