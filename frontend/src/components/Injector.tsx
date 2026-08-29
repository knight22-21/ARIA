import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, Radio, BadgeIndianRupee } from "lucide-react";
import { api, type RunResult } from "@/lib/api";
import { Button, Card, CardTitle, Select } from "@/components/ui";
import { RunModal } from "@/components/RunModal";

export function Injector({ onFired }: { onFired?: (riskEventId: string) => void }) {
  const qc = useQueryClient();
  const [scenario, setScenario] = useState("");
  const [modal, setModal] = useState<{ mode: "inject" | "recover"; scenario: string; trigger: () => Promise<RunResult> } | null>(null);

  const { data } = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
  const scenarios = data?.scenarios ?? [];
  const selected = scenario || scenarios[0] || "";

  const invalidate = useCallback(() => {
    ["summary", "pnl", "risk-events", "audit", "sankey", "escalations", "outbox"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k] }),
    );
  }, [qc]);

  const openInject = () =>
    setModal({
      mode: "inject",
      scenario: selected,
      trigger: async () => {
        const r = await api.inject(selected);
        if (r.risk_event_id) onFired?.(r.risk_event_id);
        return r as RunResult;
      },
    });

  const openRecover = () =>
    setModal({
      mode: "recover",
      scenario: selected,
      trigger: async () => {
        const r = await api.recover(selected);
        onFired?.(r.risk_event_id);
        return r;
      },
    });

  return (
    <Card className="h-full">
      <div className="flex items-center justify-between">
        <CardTitle>Live Event Injector</CardTitle>
        <span className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-accent">
          <Radio className="h-3 w-3" /> real-time
        </span>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        Fire a case through the full pipeline, or issue a <span className="text-primary">real Razorpay
        payment link</span> and watch ARIA recover it — each step unfolds live.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Select value={selected} onChange={setScenario} className="min-w-[200px] flex-1">
          {scenarios.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Button onClick={openInject} disabled={!selected}>
          <Play className="h-4 w-4" /> Fire event
        </Button>
        <Button variant="outline" onClick={openRecover} disabled={!selected}>
          <BadgeIndianRupee className="h-4 w-4" /> Recover (real link)
        </Button>
      </div>

      {modal && (
        <RunModal
          open
          mode={modal.mode}
          scenario={modal.scenario}
          trigger={modal.trigger}
          onClose={() => {
            setModal(null);
            invalidate();
          }}
        />
      )}
    </Card>
  );
}
