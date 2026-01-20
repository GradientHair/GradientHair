"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMeetingStore } from "@/store/meeting-store";
import { soundPlayer } from "@/lib/sound-player";

const typeConfig = {
  TOPIC_DRIFT: { icon: "🎯", label: "주제 이탈", color: "bg-yellow-50 border-yellow-500" },
  PRINCIPLE_VIOLATION: { icon: "⚠️", label: "원칙 위반", color: "bg-orange-50 border-orange-500" },
  PARTICIPATION_IMBALANCE: { icon: "⚖️", label: "발언 불균형", color: "bg-blue-50 border-blue-500" },
  DECISION_STYLE: { icon: "🤝", label: "의사결정 방식", color: "bg-purple-50 border-purple-500" },
};

export function InterventionToast() {
  const { currentIntervention, dismissIntervention } = useMeetingStore();

  useEffect(() => {
    if (currentIntervention) {
      soundPlayer.playAlert();
    }
  }, [currentIntervention]);

  if (!currentIntervention) return null;

  const config = typeConfig[currentIntervention.type];

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 animate-in slide-in-from-right">
      <Card className={`border-2 ${config.color}`}>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>{config.icon}</span>
            <span>{config.label}</span>
            <span className="text-xs text-gray-500 ml-auto">MeetingMod</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm">{currentIntervention.message}</p>
          {currentIntervention.violatedPrinciple && (
            <p className="text-xs text-gray-500">
              위반 원칙: {currentIntervention.violatedPrinciple}
            </p>
          )}
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" size="sm" onClick={dismissIntervention}>
              무시
            </Button>
            <Button size="sm" onClick={dismissIntervention}>
              확인
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
