"use client";

import { useEffect, useRef } from "react";
import { useMeetingStore } from "@/store/meeting-store";
import { formatTime, t } from "@/lib/i18n";

export function TranscriptView() {
  const { transcript, interventions, transcriptStream } = useMeetingStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const recentLatencies = transcript
    .map((t) => t.latencyMs)
    .filter((v): v is number => typeof v === "number")
    .slice(-10);
  const avgLatency =
    recentLatencies.length > 0
      ? Math.round(recentLatencies.reduce((sum, v) => sum + v, 0) / recentLatencies.length)
      : null;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // 자막과 개입을 시간순으로 병합
  const allItems = [
    ...transcript.map((t) => ({ ...t, itemType: "transcript" as const })),
    ...interventions.map((i) => ({ ...i, itemType: "intervention" as const })),
  ].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  return (
    <div className="h-[400px] overflow-y-auto bg-white rounded-lg border p-4 space-y-3">
      {avgLatency !== null && (
        <div className="text-xs text-gray-500">{t("transcript.avgLatency", { latency: avgLatency })}</div>
      )}
      {allItems.map((item) => {
        if (item.itemType === "transcript") {
          const time = formatTime(item.timestamp);
          return (
            <div key={item.id} className="text-sm">
              <span className="text-gray-500">[{time}]</span>{" "}
              <span className="font-semibold">{item.speaker}:</span>{" "}
              <span>{item.text}</span>
              {typeof item.latencyMs === "number" && (
                <span className="ml-2 text-xs text-gray-400">({Math.round(item.latencyMs)}ms)</span>
              )}
            </div>
          );
        } else {
          return (
            <div key={item.id} className="border-t border-b border-orange-300 py-2 my-2 bg-orange-50">
              <div className="text-sm text-orange-700">
                🤖 <span className="font-semibold">[{item.type}]</span> {item.message}
              </div>
            </div>
          );
        }
      })}
      {transcriptStream && transcriptStream.text && (
        <div className="text-sm italic text-gray-600">
          <span className="text-gray-500">
            [{formatTime(transcriptStream.timestamp)}]
          </span>{" "}
          <span className="font-semibold">{transcriptStream.speaker}:</span>{" "}
          <span>{transcriptStream.text}</span>
          <span className="ml-1 animate-pulse">▌</span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
