"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useMeetingStore } from "@/store/meeting-store";
import { getApiBase } from "@/lib/api";

type ActionItem = {
  item: string;
  owner: string;
  due: string;
};

const parseActionItems = (content?: string | null): ActionItem[] => {
  if (!content) return [];
  if (content.includes("추출된 Action Item이 없습니다.")) return [];
  const lines = content.split("\n").map((line) => line.trim());
  const tableRows = lines.filter((line) => line.startsWith("|") && !line.includes("---"));
  const tableItems = tableRows
    .filter(
      (line) =>
        !(line.toLowerCase().includes("action") && line.toLowerCase().includes("owner"))
    )
    .map((line) => line.split("|").map((cell) => cell.trim()).filter(Boolean))
    .filter((cells) => cells.length >= 3)
    .map((cells) => ({
      item: cells[0],
      owner: cells[1],
      due: cells[2],
    }));

  if (tableItems.length > 0) {
    return tableItems;
  }

  const bulletLines = lines.filter((line) => line.startsWith("-"));
  return bulletLines
    .map((line) => line.replace(/^-\s*\[\s*\]\s*/, "").replace(/^-/, "").trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      const parts = line.split("|").map((part) => part.trim());
      const item = parts[0] ?? "";
      const ownerPart = parts.find((part) => part.toLowerCase().startsWith("owner:"));
      const duePart = parts.find((part) => part.toLowerCase().startsWith("due:"));
      return {
        item,
        owner: ownerPart ? ownerPart.split(":", 2)[1]?.trim() ?? "" : "",
        due: duePart ? duePart.split(":", 2)[1]?.trim() ?? "" : "",
      };
    })
    .filter((entry) => entry.item.length > 0);
};

export default function ReviewPage() {
  const params = useParams();
  const meetingId = params.id as string;
  const apiBase = getApiBase();
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [actionItemsStatus, setActionItemsStatus] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const { title, transcript, interventions, speakerStats, participants } =
    useMeetingStore();

  useEffect(() => {
    let isMounted = true;
    let attempts = 0;
    const maxAttempts = 10;
    const intervalMs = 2500;

    const load = async () => {
      attempts += 1;
      try {
        const response = await fetch(`${apiBase}/meetings/${meetingId}/files`);
        if (!response.ok) {
          throw new Error("Failed to load meeting files");
        }
        const data = await response.json();
        const parsed = parseActionItems(data.actionItems);

        if (!isMounted) return;

        if (parsed.length > 0) {
          setActionItems(parsed);
          setActionItemsStatus("ready");
          return;
        }

        if (data.actionItems) {
          setActionItemsStatus("empty");
          return;
        }
      } catch {
        if (!isMounted) return;
        if (attempts >= maxAttempts) {
          setActionItemsStatus("error");
          return;
        }
      }

      if (attempts < maxAttempts && isMounted) {
        setActionItemsStatus("loading");
        setTimeout(load, intervalMs);
      } else if (isMounted) {
        setActionItemsStatus("empty");
      }
    };

    load();
    return () => {
      isMounted = false;
    };
  }, [apiBase, meetingId]);

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

      <Card>
        <CardHeader>
          <CardTitle>Action Items</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {actionItemsStatus === "loading" && (
            <p className="text-gray-500">Action Item을 생성 중입니다...</p>
          )}
          {actionItemsStatus === "error" && (
            <p className="text-red-500">Action Item을 불러오지 못했어요.</p>
          )}
          {actionItemsStatus !== "loading" && actionItems.length === 0 && (
            <p className="text-gray-500">등록된 Action Item이 없습니다.</p>
          )}
          {actionItems.length > 0 && (
            <div className="space-y-2">
              {actionItems.map((item, index) => (
                <div key={`${item.item}-${index}`} className="rounded border border-gray-100 p-3">
                  <p className="font-medium">{item.item}</p>
                  <p className="text-gray-500">
                    {item.owner ? `담당자: ${item.owner}` : "담당자 미정"} ·{" "}
                    {item.due ? `기한: ${item.due}` : "기한 없음"}
                  </p>
                </div>
              ))}
            </div>
          )}
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
