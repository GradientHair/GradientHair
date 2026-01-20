"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const defaultPrinciples: Record<string, string> = {
  agile: `# Agile Meeting Principles

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

  "aws-leadership": `# AWS Leadership Principles for Meetings

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
};

export default function PrinciplesPage() {
  const [principles, setPrinciples] = useState(defaultPrinciples);
  const [activeTab, setActiveTab] = useState("agile");
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    // TODO: API 호출하여 저장
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">회의 원칙 관리</h2>
        <Button onClick={handleSave}>
          {saved ? "저장됨" : "저장"}
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="agile">Agile 원칙</TabsTrigger>
          <TabsTrigger value="aws-leadership">AWS Leadership</TabsTrigger>
          <TabsTrigger value="custom">커스텀</TabsTrigger>
        </TabsList>

        <TabsContent value="agile">
          <Card>
            <CardHeader>
              <CardTitle>Agile Meeting Principles</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={principles.agile}
                onChange={(e) =>
                  setPrinciples({ ...principles, agile: e.target.value })
                }
                rows={20}
                className="font-mono text-sm"
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="aws-leadership">
          <Card>
            <CardHeader>
              <CardTitle>AWS Leadership Principles</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={principles["aws-leadership"]}
                onChange={(e) =>
                  setPrinciples({ ...principles, "aws-leadership": e.target.value })
                }
                rows={20}
                className="font-mono text-sm"
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="custom">
          <Card>
            <CardHeader>
              <CardTitle>커스텀 원칙</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="# 우리팀 회의 원칙&#10;&#10;1. ..."
                rows={20}
                className="font-mono text-sm"
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
