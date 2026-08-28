import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, Loader2, Radio } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button, Card, CardTitle, Select } from "@/components/ui";

export function Injector({ onFired }: { onFired?: (riskEventId: string) => void }) {
  const qc = useQueryClient();
  const [scenario, setScenario] = useState("");
  const { data } = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
  const scenarios = data?.scenarios ?? [];
  const selected = scenario || scenarios[0] || "";

  const invalidate = () =>
    ["summary", "pnl", "risk-events", "audit", "sankey", "escalations", "outbox"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k] }),
    );

  const fire = useMutation({
    mutationFn: () => api.inject(selected),
    onSuccess: (r) => {
      const bits = [r.outcome && `→ ${r.outcome}`, r.diagnosis && `· ${r.diagnosis.root_cause_category}`]
        .filter(Boolean)
        .join(" ");
      toast.success(`Injected ${selected.replace(/_/g, " ")}`, { description: bits || undefined });
      if (r.risk_event_id) onFired?.(r.risk_event_id);
      invalidate();
    },
    onError: (e: Error) => toast.error("Inject failed", { description: e.message }),
  });

  const track = useMutation({
    mutationFn: api.runOutcomeTracker,
    onSuccess: () => {
      toast.success("Outcome tracker ran");
      invalidate();
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
        Fire a synthetic payment event through the full pipeline — detection → reasoning →
        action — and watch it land in the feed below.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Select value={selected} onChange={setScenario} className="min-w-[220px] flex-1">
          {scenarios.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Button onClick={() => fire.mutate()} disabled={fire.isPending || !selected}>
          {fire.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Fire event
        </Button>
        <Button variant="outline" onClick={() => track.mutate()} disabled={track.isPending}>
          {track.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Run tracker
        </Button>
      </div>
    </Card>
  );
}
