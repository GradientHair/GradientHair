"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { getApiBase } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Principle = {
  id: string;
  name: string;
  content: string;
  source: "preset" | "custom";
};

const defaultPrinciples: Principle[] = [
  {
    id: "agile",
    name: "Agile 원칙",
    source: "preset",
    content: `# Agile Meeting Principles

1. **수평적 의사결정**
   모든 참석자의 의견을 동등하게 존중합니다.

2. **타임박스**
   정해진 시간 내에 논의를 완료합니다.

3. **Action-oriented**
   모든 논의는 Action Item으로 연결됩니다.

4. **짧고 집중**
   불필요한 발언을 최소화합니다.

5. **투명성**
   정보 공유에 숨김이 없습니다.`,
  },
  {
    id: "aws-leadership",
    name: "AWS Leadership",
    source: "preset",
    content: `# AWS Leadership Principles for Meetings

1. **Customer Obsession**
   고객 관점에서 논의합니다.

2. **Ownership**
   책임감 있는 의견을 제시합니다.

3. **Disagree and Commit**
   이견을 표출한 후 결정을 따릅니다.

4. **Have Backbone; Disagree**
   동의하지 않으면 정중히 반박합니다.

5. **Dive Deep**
   세부사항까지 파악합니다.

6. **Bias for Action**
   빠른 결정, 실행 우선으로 진행합니다.`,
  },
];

const presetIds = new Set(["agile", "aws-leadership"]);

const buildTemplate = (name: string) => `# ${name}

1. **핵심 원칙**
   한 문장으로 요약합니다.

2. **행동 기준**
   회의에서 지켜야 할 행동을 적습니다.

3. **피드백 방법**
   문제가 생겼을 때 어떻게 논의할지 적습니다.`;

export default function PrinciplesPage() {
  const apiBase = getApiBase();
  const [principles, setPrinciples] = useState<Principle[]>(defaultPrinciples);
  const [savedPrinciples, setSavedPrinciples] = useState<Principle[]>(defaultPrinciples);
  const [activeTab, setActiveTab] = useState(principles[0]?.id ?? "");
  const [savedId, setSavedId] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const loadPrinciples = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${apiBase}/principles`);
        if (!response.ok) {
          throw new Error("Failed to load principles");
        }
        const data = await response.json();
        if (!Array.isArray(data.principles)) {
          throw new Error("Invalid principles response");
        }
        const mapped = data.principles.map(
          (principle: { id: string; name: string; content: string }) => ({
            id: principle.id,
            name: principle.name,
            content: principle.content,
            source: presetIds.has(principle.id) ? "preset" : "custom",
          })
        );
        if (isMounted) {
          const next = mapped.length > 0 ? mapped : defaultPrinciples;
          setPrinciples(next);
          setSavedPrinciples(next);
          setActiveTab(next[0]?.id ?? "");
        }
      } catch {
        if (isMounted) {
          setPrinciples(defaultPrinciples);
          setSavedPrinciples(defaultPrinciples);
          setActiveTab(defaultPrinciples[0]?.id ?? "");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    loadPrinciples();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSave = async (id: string) => {
    // TODO: API 호출하여 저장
    const currentContent = principles.find((item) => item.id === id)?.content;
    if (currentContent === undefined) return;
    try {
      const response = await fetch(`${apiBase}/principles/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: currentContent }),
      });
      if (!response.ok) {
        throw new Error("Failed to save");
      }
      const updated = await response.json();
      setPrinciples((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, content: updated.content ?? currentContent, name: updated.name ?? item.name }
            : item
        )
      );
      setSavedPrinciples((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, content: updated.content ?? currentContent, name: updated.name ?? item.name }
            : item
        )
      );
      setSavedId(id);
      setTimeout(() => setSavedId((prev) => (prev === id ? null : prev)), 2000);
    } catch {
      // keep local changes if save fails
    }
  };

  const handleCancel = (id: string) => {
    const savedContent = savedPrinciples.find((item) => item.id === id)?.content;
    if (savedContent === undefined) return;
    setPrinciples((prev) =>
      prev.map((item) => (item.id === id ? { ...item, content: savedContent } : item))
    );
  };

  const handleAdd = async () => {
    const trimmedName = draftName.trim();
    if (!trimmedName) return;
    const content = draftContent.trim().length > 0 ? draftContent : buildTemplate(trimmedName);
    try {
      const response = await fetch(`${apiBase}/principles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmedName, content }),
      });
      if (!response.ok) {
        throw new Error("Failed to create");
      }
      const created = await response.json();
      const nextPrinciple: Principle = {
        id: created.id,
        name: created.name ?? trimmedName,
        content,
        source: "custom",
      };
      setPrinciples((prev) => [...prev, nextPrinciple]);
      setSavedPrinciples((prev) => [...prev, nextPrinciple]);
      setActiveTab(created.id);
      setDraftName("");
      setDraftContent("");
      setIsDialogOpen(false);
    } catch {
      // keep dialog open if create fails
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("이 원칙을 삭제할까요?")) return;
    try {
      const response = await fetch(`${apiBase}/principles/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete");
      }
      setPrinciples((prev) => {
        const next = prev.filter((item) => item.id !== id);
        if (activeTab === id) {
          setActiveTab(next[0]?.id ?? "");
        }
        return next;
      });
      setSavedPrinciples((prev) => prev.filter((item) => item.id !== id));
    } catch {
      // ignore delete failures
    }
  };

  const { presetCount, customCount } = useMemo(() => {
    return {
      presetCount: principles.filter((p) => p.source === "preset").length,
      customCount: principles.filter((p) => p.source === "custom").length,
    };
  }, [principles]);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <Card className="border-0 bg-gradient-to-br from-amber-50 via-white to-emerald-50 shadow-sm">
        <CardHeader className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <CardTitle className="text-2xl">회의 원칙 관리</CardTitle>
              <CardDescription className="text-sm">
                회의가 흐트러지지 않도록 팀의 합의된 기준을 정리하고 공유하세요.
              </CardDescription>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <Badge variant="secondary">총 {principles.length}개</Badge>
                <span>기본 {presetCount} · 커스텀 {customCount}</span>
              </div>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="w-full sm:w-auto" disabled={isLoading}>
                    새 원칙 추가
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>새 원칙 추가</DialogTitle>
                    <DialogDescription>
                      팀 이름에 맞는 원칙 이름과 초안을 적어두면 빠르게 시작할 수 있어요.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">원칙 이름</label>
                      <Input
                        value={draftName}
                        onChange={(e) => setDraftName(e.target.value)}
                        placeholder="예: 디자인 스프린트 원칙"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">초안 내용</label>
                      <Textarea
                        value={draftContent}
                        onChange={(e) => setDraftContent(e.target.value)}
                        placeholder="# 원칙 제목\n\n1. ..."
                        rows={8}
                        className="font-mono text-sm"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button
                      onClick={handleAdd}
                      disabled={draftName.trim().length === 0}
                    >
                      추가하기
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="gap-4">
        <Card className="border-dashed">
          <CardContent className="py-4">
            <TabsList className="flex h-auto w-full flex-wrap justify-start gap-2 bg-transparent p-0">
              {principles.map((principle) => (
                <TabsTrigger
                  key={principle.id}
                  value={principle.id}
                  className="h-auto flex-none px-3 py-2"
                >
                  <span>{principle.name}</span>
                  <Badge
                    variant="outline"
                    className="ml-1 border-muted-foreground/30 text-muted-foreground"
                  >
                    {principle.source === "preset" ? "기본" : "커스텀"}
                  </Badge>
                </TabsTrigger>
              ))}
            </TabsList>
          </CardContent>
        </Card>

        {principles.map((principle) => {
          const savedContent = savedPrinciples.find((item) => item.id === principle.id)?.content ?? "";
          const isDirty = principle.content !== savedContent;
          const canDelete = principle.source === "custom";
          return (
            <TabsContent key={principle.id} value={principle.id} className="space-y-6">
              <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
                <Card className="border-none bg-muted/30 shadow-none">
                  <CardHeader>
                    <CardTitle className="text-lg">작성 가이드</CardTitle>
                    <CardDescription>
                      Markdown 형식으로 작성하면 팀원들이 읽기 쉬워요.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm text-muted-foreground">
                    <div>핵심 원칙은 3~6개로 간결하게 정리하세요.</div>
                    <div>행동 기준은 동사로 시작하면 명확해집니다.</div>
                    <div>갈등 해결 방식을 한 줄로 추가하세요.</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="space-y-1">
                        <CardTitle>{principle.name}</CardTitle>
                        <CardDescription>
                          팀이 공유할 원칙 문서를 자유롭게 편집하세요.
                        </CardDescription>
                      </div>
                      <Button
                        variant="ghost"
                        className="text-destructive hover:text-destructive disabled:text-muted-foreground"
                        onClick={() => handleDelete(principle.id)}
                        disabled={!canDelete}
                      >
                        삭제
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Textarea
                      value={principle.content}
                      onChange={(e) =>
                        setPrinciples((prev) =>
                          prev.map((item) =>
                            item.id === principle.id
                              ? { ...item, content: e.target.value }
                              : item
                          )
                        )
                      }
                      rows={18}
                      className="min-h-[360px] font-mono text-sm"
                    />
                  </CardContent>
                  <CardFooter className="flex flex-wrap justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={() => handleCancel(principle.id)}
                      disabled={!isDirty}
                    >
                      취소
                    </Button>
                    <Button
                      onClick={() => handleSave(principle.id)}
                      disabled={!isDirty}
                    >
                      {savedId === principle.id ? "저장됨" : "저장"}
                    </Button>
                  </CardFooter>
                </Card>
              </div>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
