"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useMeetingStore } from "@/store/meeting-store";
import { getApiBase } from "@/lib/api";
import { t } from "@/lib/i18n";

type ActionItem = {
  item: string;
  owner: string;
  due: string;
};

const parseActionItems = (content?: string | null): ActionItem[] => {
  if (!content) return [];
  if (content.includes("추출된 Action Item이 없습니다.") || content.includes("No action items were extracted.")) return [];
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
            {t("review.saved")}
          </p>
          <p className="text-sm text-green-600">
            meetings/{meetingId}/
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("review.summaryTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p><strong>{t("history.meetingLabel")}:</strong> {title || meetingId}</p>
            <p><strong>{t("review.participants")}:</strong> {participants.map((p) => p.name).join(", ") || t("common.none")}</p>
            <p><strong>{t("review.utterances")}:</strong> {transcript.length}</p>
            <p><strong>{t("review.interventions")}:</strong> {interventions.length}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t("review.speakerStats")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {participants.length === 0 && (
              <p className="text-gray-500 text-sm">{t("review.speakerStatsEmpty")}</p>
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
            <CardTitle>{t("review.interventionLog")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              {interventions.length === 0 && (
                <p className="text-gray-500">{t("review.interventionEmpty")}</p>
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
          <CardTitle>{t("review.savedFiles")}</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-sm space-y-1">
            <li>{t("review.preparationFile")}</li>
            <li>{t("review.transcriptFile")}</li>
            <li>{t("review.interventionsFile")}</li>
            <li>{t("review.summaryFile")}</li>
            <li>action-items.md - Action Items</li>
          </ul>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t("review.actionItemsTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {actionItemsStatus === "loading" && (
            <p className="text-gray-500">{t("review.actionItemsLoading")}</p>
          )}
          {actionItemsStatus === "error" && (
            <p className="text-red-500">{t("review.actionItemsError")}</p>
          )}
          {actionItemsStatus !== "loading" && actionItems.length === 0 && (
            <p className="text-gray-500">{t("review.actionItemsEmpty")}</p>
          )}
          {actionItems.length > 0 && (
            <div className="space-y-2">
              {actionItems.map((item, index) => (
                <div key={`${item.item}-${index}`} className="rounded border border-gray-100 p-3">
                  <p className="font-medium">{item.item}</p>
                  <p className="text-gray-500">
                    {item.owner
                      ? t("review.actionItemOwner", { owner: item.owner })
                      : t("review.actionItemOwnerUnknown")}{" "}
                    ·{" "}
                    {item.due
                      ? t("review.actionItemDue", { due: item.due })
                      : t("review.actionItemDueNone")}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button onClick={() => (window.location.href = "/")}>
          {t("review.startNew")}
        </Button>
      </div>
    </div>
  );
}
