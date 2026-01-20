"use client";

import { Progress } from "@/components/ui/progress";
import { useMeetingStore } from "@/store/meeting-store";
import { t } from "@/lib/i18n";

export function SpeakerStats() {
  const { speakerStats, participants } = useMeetingStore();

  return (
    <div className="space-y-3">
      {participants.map((p) => {
        const stats = speakerStats[p.name] || { percentage: 0, count: 0 };
        const isLow = stats.percentage < 15 && stats.percentage > 0;
        const isHigh = stats.percentage > 50;

        return (
          <div key={p.id} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className={isLow ? "text-orange-600" : isHigh ? "text-red-600" : ""}>
                {p.name}
              </span>
              <span className="text-gray-500">
                {t("speakerStats.percentageCount", {
                  percentage: stats.percentage,
                  count: stats.count,
                })}
              </span>
            </div>
            <Progress
              value={stats.percentage}
              className={isLow ? "bg-orange-100" : isHigh ? "bg-red-100" : ""}
            />
            {isLow && <span className="text-xs text-orange-600">{t("speakerStats.imbalance")}</span>}
          </div>
        );
      })}
    </div>
  );
}
