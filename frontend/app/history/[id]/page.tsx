"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getApiBase } from "@/lib/api";
import { formatDateTime, t } from "@/lib/i18n";

type MeetingFiles = {
  id: string;
  preparation?: string | null;
  transcript?: string | null;
  interventions?: string | null;
  actionItems?: string | null;
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

type ActionItem = {
  item: string;
  owner: string;
  due: string;
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
    if (line.startsWith("- **제목**:") || line.startsWith("- **Title**:")) {
      title = line.split(":", 2)[1]?.trim() ?? "";
      continue;
    }
    if (line.startsWith("- **일시**:") || line.startsWith("- **Date/Time**:")) {
      scheduledAt = line.split(":", 2)[1]?.trim() ?? "";
      continue;
    }
    if (line.startsWith("## 참석자") || line.startsWith("## Participants")) {
      inParticipants = true;
      inAgenda = false;
      continue;
    }
    if (line.startsWith("## 아젠다") || line.startsWith("## Agenda")) {
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
      if (cells.length >= 2 && cells[0] !== "이름" && cells[0] !== "Name") {
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
    const typeLine = lines.find((line) => line.startsWith("- **유형**:") || line.startsWith("- **Type**:"));
    const messageLine = lines.find((line) => line.startsWith("- **메시지**:") || line.startsWith("- **Message**:"));
    parsed.push({
      id: `inv_${index}`,
      type: typeLine ? typeLine.split(":", 2)[1]?.trim() ?? "" : "INFO",
      message: messageLine ? messageLine.split(":", 2)[1]?.trim() ?? "" : "",
    });
  });
  return parsed.filter((inv) => inv.message.length > 0);
};

const parseActionItems = (content?: string | null): ActionItem[] => {
  if (!content) return [];
  if (content.includes("추출된 Action Item이 없습니다.") || content.includes("No action items were extracted.")) {
    return [];
  }
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

const formatMeetingDate = (value?: string | null) => formatDateTime(value);

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
          setError(t("history.loadError"));
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
  const actionItems = useMemo(
    () => parseActionItems(meeting?.actionItems),
    [meeting?.actionItems]
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Card className="border-0 bg-gradient-to-br from-slate-50 via-white to-emerald-50 shadow-sm">
        <CardHeader className="space-y-2">
          <CardTitle className="text-2xl">
            {preparation.title || meeting?.id || t("home.pastMeetings")}
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
            {t("history.loading")}
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
              <CardTitle>{t("history.summaryTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p>
                  <strong>{t("history.meetingLabel")}:</strong> {preparation.title || meetingId}
                </p>
                <p>
                  <strong>{t("history.participantsLabel")}:</strong>{" "}
                  {preparation.participants.map((p) => p.name).join(", ") || t("common.none")}
                </p>
                <p>
                  <strong>{t("history.utterancesLabel")}:</strong> {transcriptCount}
                </p>
                <p>
                  <strong>{t("history.interventionsLabel")}:</strong> {interventions.length}
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>{t("history.speakerStats")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {preparation.participants.length === 0 && (
                  <p className="text-gray-500 text-sm">{t("history.speakerStatsEmpty")}</p>
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
                <CardTitle>{t("history.interventionLog")}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {interventions.length === 0 && (
                    <p className="text-gray-500">{t("history.interventionEmpty")}</p>
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
              <CardTitle>{t("history.savedFiles")}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-1">
                <li>{t("history.preparationFile")}</li>
                <li>{t("history.transcriptFile")}</li>
                <li>{t("history.interventionsFile")}</li>
                <li>{t("history.summaryFile")}</li>
                <li>action-items.md - Action Items</li>
              </ul>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>{t("history.actionItemsTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {actionItems.length === 0 && (
                <p className="text-muted-foreground">{t("history.actionItemsEmpty")}</p>
              )}
              {actionItems.length > 0 && (
                <div className="space-y-2">
                  {actionItems.map((item, index) => (
                    <div key={`${item.item}-${index}`} className="rounded border border-slate-100 p-3">
                      <p className="font-medium">{item.item}</p>
                      <p className="text-muted-foreground">
                        {item.owner
                          ? t("history.actionItemOwner", { owner: item.owner })
                          : t("history.actionItemOwnerUnknown")}{" "}
                        ·{" "}
                        {item.due
                          ? t("history.actionItemDue", { due: item.due })
                          : t("history.actionItemDueNone")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <div className="flex justify-center">
        <Button asChild>
          <Link href="/">{t("history.startNew")}</Link>
        </Button>
      </div>
    </div>
  );
}
