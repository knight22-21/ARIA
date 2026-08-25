import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, Loader2, Activity } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui";

export function Injector() {
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
      toast.success(`Injected ${selected}`, { description: bits || undefined });
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
    <div className="glass rounded-xl p-5">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <Activity className="h-4 w-4 text-primary" /> Live Event Injector
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={selected}
          onChange={(e) => setScenario(e.target.value)}
          className="flex-1 rounded-lg border border-border bg-background/60 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50"
        >
          {scenarios.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <Button onClick={() => fire.mutate()} disabled={fire.isPending || !selected}>
          {fire.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Fire event
        </Button>
        <Button variant="outline" onClick={() => track.mutate()} disabled={track.isPending}>
          Run tracker
        </Button>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        Fires a synthetic payment event through the full pipeline — watch it appear below.
      </p>
    </div>
  );
}
