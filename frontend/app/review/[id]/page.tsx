"use client";

import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useMeetingStore } from "@/store/meeting-store";

export default function ReviewPage() {
  const params = useParams();
  const meetingId = params.id as string;
  const { title, transcript, interventions, speakerStats, participants } =
    useMeetingStore();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Card className="bg-green-50 border-green-500">
        <CardContent className="pt-4">
          <p className="text-green-700">
            회의록이 저장되었습니다
          </p>
          <p className="text-sm text-green-600">
            meetings/{meetingId}/
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>회의 요약</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p><strong>회의:</strong> {title || meetingId}</p>
            <p><strong>참석자:</strong> {participants.map((p) => p.name).join(", ") || "없음"}</p>
            <p><strong>발화 수:</strong> {transcript.length}</p>
            <p><strong>Agent 개입:</strong> {interventions.length}회</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>참여도 분포</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {participants.length === 0 && (
              <p className="text-gray-500 text-sm">참석자 정보 없음</p>
            )}
            {participants.map((p) => {
              const stats = speakerStats[p.name] || { percentage: 0 };
              return (
                <div key={p.id} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>{p.name}</span>
                    <span>{stats.percentage}%</span>
                  </div>
                  <Progress value={stats.percentage} />
                </div>
              );
            })}
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

      <div className="flex justify-center">
        <Button onClick={() => (window.location.href = "/")}>
          새 회의 시작
        </Button>
      </div>
    </div>
  );
}
