"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useMeetingStore } from "@/store/meeting-store";

export default function MeetingPrepPage() {
  const router = useRouter();
  const {
    title,
    setTitle,
    agenda,
    setAgenda,
    participants,
    addParticipant,
    removeParticipant,
    selectedPrinciples,
    setSelectedPrinciples,
  } = useMeetingStore();

  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");

  const principles = [
    { id: "agile", name: "Agile 원칙" },
    { id: "aws-leadership", name: "AWS Leadership Principles" },
  ];

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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
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
                  <span>{p.name} ({p.role})</span>
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
