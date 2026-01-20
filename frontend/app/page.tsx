"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { getApiBase } from "@/lib/api";
import { useMeetingStore } from "@/store/meeting-store";
import { formatDateTime, t } from "@/lib/i18n";

type PastMeeting = {
  id: string;
  title?: string | null;
  scheduledAt?: string | null;
  updatedAt?: string | null;
  hasTranscript?: boolean;
  hasInterventions?: boolean;
};

const formatMeetingDate = (value?: string | null) => formatDateTime(value);

export default function MeetingPrepPage() {
  const router = useRouter();
  const apiBase = getApiBase();
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
    { id: "agile", name: t("home.defaultAgilePrinciples") },
    { id: "aws-leadership", name: "AWS Leadership Principles" },
  ]);
  const [pastMeetings, setPastMeetings] = useState<PastMeeting[]>([]);
  const [pastMeetingsLoading, setPastMeetingsLoading] = useState(true);
  const [pastMeetingsError, setPastMeetingsError] = useState("");

  useEffect(() => {
    let isMounted = true;
    const loadPrinciples = async () => {
      try {
        const response = await fetch(`${apiBase}/principles`);
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

  useEffect(() => {
    let isMounted = true;
    const loadPastMeetings = async () => {
      setPastMeetingsLoading(true);
      setPastMeetingsError("");
      try {
        const response = await fetch(`${apiBase}/meetings`);
        if (!response.ok) {
          throw new Error("Failed to load meetings");
        }
        const data = await response.json();
        if (!Array.isArray(data.meetings)) {
          throw new Error("Invalid meetings response");
        }
        if (isMounted) {
          setPastMeetings(data.meetings);
        }
      } catch {
        if (isMounted) {
          setPastMeetingsError(t("home.pastMeetingsError"));
        }
      } finally {
        if (isMounted) {
          setPastMeetingsLoading(false);
        }
      }
    };
    loadPastMeetings();
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

  const handleStartMeeting = async (mode: "audio" | "agent") => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const meetingId = `${timestamp}-${title.toLowerCase().replace(/\s+/g, "-")}`;
    const modeQuery = `?mode=${mode}`;

    // API 호출하여 회의 생성
    let navigated = false;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 4000);
      const response = await fetch(`${apiBase}/meetings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          agenda,
          participants,
          principleIds: selectedPrinciples,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (response.ok) {
        const data = (await response.json()) as { id?: string };
        router.push(`/meeting/${data.id ?? meetingId}${modeQuery}`);
        navigated = true;
      }
    } catch {
      // 에이전트 모드/오프라인 환경에서 백엔드 없이도 동작
    }
    if (!navigated) {
      router.push(`/meeting/${meetingId}${modeQuery}`);
    }
  };

  const togglePrinciple = (id: string) => {
    if (selectedPrinciples.includes(id)) {
      setSelectedPrinciples(selectedPrinciples.filter((p) => p !== id));
    } else {
      setSelectedPrinciples([...selectedPrinciples, id]);
    }
  };

  const selectedPrincipleNames = principles
    .filter((principle) => selectedPrinciples.includes(principle.id))
    .map((principle) => principle.name);

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
    const roleKeywords = new Set(
      t("home.calendarRoles")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    );
    const statusKeywords = new Set(
      t("home.calendarStatusKeywords")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    );
    const ignoreAgendaKeywords = t("home.calendarIgnoreKeywords")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    const isDateLine = (line: string) =>
      /(\bAM\b|\bPM\b|\d{1,2}:\d{2}|월|일|\bJan\b|\bFeb\b|\bMar\b|\bApr\b|\bMay\b|\bJun\b|\bJul\b|\bAug\b|\bSep\b|\bOct\b|\bNov\b|\bDec\b)/i.test(
        line
      );

    const isLikelyName = (line: string) => {
      if (line.toLowerCase().includes(t("home.calendarIgnoreGreeting").toLowerCase())) return false;
      if (line.includes("@")) return false;
      if (/[0-9]/.test(line)) return false;
      if (line.toLowerCase().includes(t("home.calendarIgnoreGuests").toLowerCase())) return false;
      if (ignoreAgendaKeywords.some((keyword) => line.includes(keyword))) return false;
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
    <div className="max-w-5xl mx-auto space-y-6">
      <Tabs defaultValue="prepare" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="prepare">{t("home.tab.prepare")}</TabsTrigger>
          <TabsTrigger value="history">{t("home.tab.history")}</TabsTrigger>
        </TabsList>

        <TabsContent value="prepare" className="space-y-6">
          <Card className="border-0 bg-gradient-to-br from-amber-50 via-white to-emerald-50 shadow-sm">
            <CardHeader className="space-y-3">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-2">
                  <CardTitle className="text-2xl">{t("home.title")}</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {t("home.subtitle")}
                  </p>
                </div>
                <Dialog open={pasteModalOpen} onOpenChange={setPasteModalOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" className="w-full sm:w-auto">
                      {t("home.pasteMeeting")}
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-xl">
                    <DialogHeader>
                      <DialogTitle>{t("home.pasteDialogTitle")}</DialogTitle>
                      <DialogDescription>
                        {t("home.pasteDialogDesc")}
                      </DialogDescription>
                    </DialogHeader>
                    <Textarea
                      placeholder={t("home.pastePlaceholder")}
                      value={pastedText}
                      onChange={(e) => setPastedText(e.target.value)}
                      rows={10}
                    />
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setPasteModalOpen(false)}>
                        {t("common.cancel")}
                      </Button>
                      <Button onClick={handlePasteSubmit} disabled={!pastedText.trim()}>
                        {t("home.pasteAction")}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("home.meetingTitle")}</CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                placeholder={t("home.meetingTitlePlaceholder")}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{t("home.participants")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    placeholder={t("home.participantName")}
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                  />
                  <Input
                    placeholder={t("home.participantRole")}
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                  />
                  <Button onClick={handleAddParticipant} className="sm:shrink-0">
                    {t("common.add")}
                  </Button>
                </div>
                <div className="space-y-2">
                  {participants.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border border-muted/30 bg-white/80 px-3 py-2"
                    >
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
                <CardTitle>{t("home.principles")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {principles.map((p) => (
                  <div
                    key={p.id}
                    className={`rounded-lg border px-3 py-2 transition ${
                      selectedPrinciples.includes(p.id)
                        ? "border-emerald-200 bg-emerald-50"
                        : "border-muted/30 bg-white"
                    }`}
                    onClick={() => togglePrinciple(p.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        togglePrinciple(p.id);
                      }
                    }}
                    role="button"
                    tabIndex={0}
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
              <CardTitle>{t("home.selectedPrinciples")}</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedPrincipleNames.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {t("home.selectedPrinciplesEmpty")}
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selectedPrincipleNames.map((name) => (
                    <span
                      key={name}
                      className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("home.agenda")}</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder={t("home.agendaPlaceholder")}
                value={agenda}
                onChange={(e) => setAgenda(e.target.value)}
                rows={10}
              />
            </CardContent>
          </Card>

          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Button
              size="lg"
              onClick={() => handleStartMeeting("audio")}
              disabled={!title || participants.length === 0}
            >
              {t("home.startAudio")}
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => handleStartMeeting("agent")}
              disabled={!title || participants.length === 0}
            >
              {t("home.startAgent")}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-6">
          <Card className="border-none bg-muted/30 shadow-none">
            <CardHeader>
              <CardTitle>{t("home.pastMeetings")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {pastMeetingsLoading && (
                <p className="text-sm text-muted-foreground">{t("home.pastMeetingsLoading")}</p>
              )}
              {pastMeetingsError && (
                <p className="text-sm text-red-500">{pastMeetingsError}</p>
              )}
              {!pastMeetingsLoading && !pastMeetingsError && pastMeetings.length === 0 && (
                <p className="text-sm text-muted-foreground">{t("home.pastMeetingsEmpty")}</p>
              )}
              {!pastMeetingsLoading &&
                !pastMeetingsError &&
                pastMeetings.map((meeting) => (
                  <Link
                    key={meeting.id}
                    href={`/history/${meeting.id}`}
                    className="block"
                  >
                    <div className="flex flex-col gap-3 rounded-lg border border-muted/30 bg-white/80 p-4 transition hover:border-emerald-200 hover:bg-emerald-50/40 sm:flex-row sm:items-center sm:justify-between">
                      <div className="space-y-1">
                        <p className="text-base font-semibold">{meeting.title || meeting.id}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatMeetingDate(meeting.scheduledAt || meeting.updatedAt)}
                        </p>
                        <p className="text-xs text-muted-foreground">meetings/{meeting.id}</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span
                          className={`rounded-full px-2 py-1 ${
                            meeting.hasTranscript
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {t("home.statusTranscripts")}
                        </span>
                        <span
                          className={`rounded-full px-2 py-1 ${
                            meeting.hasInterventions
                              ? "bg-amber-50 text-amber-700"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {t("home.statusInterventions")}
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
