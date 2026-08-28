import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "@/lib/api";
import { Card, CardTitle, EmptyState, Skeleton } from "@/components/ui";

interface FeedEvent {
  event_type: string;
  actor: string;
  created_at: string;
  correlation_id?: string | null;
  entity_id?: string | null;
}

const DOT: Record<string, string> = {
  RISK_DETECTED: "bg-info",
  POLICY_CHECKED: "bg-muted-foreground",
  DIAGNOSIS_PRODUCED: "bg-accent",
  INTERVENTION_PLANNED: "bg-accent",
  ACTION_EXECUTED: "bg-primary",
  AGENT_DECISION: "bg-muted-foreground",
  ESCALATION_RAISED: "bg-warning",
  STOPPING_RULE_FIRED: "bg-danger",
  RECOVERY_ATTRIBUTED: "bg-primary",
  OUTCOME_DETECTED: "bg-primary",
  HUMAN_APPROVED: "bg-primary",
  HUMAN_REJECTED: "bg-danger",
};

export function LiveFeed({
  focusId,
  onShowAll,
}: {
  focusId?: string | null;
  onShowAll?: () => void;
}) {
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);
  const seq = useRef(0);

  useEffect(() => {
    api
      .audit("?limit=30")
      .then((rows) => setEvents(rows))
      .catch(() => {})
      .finally(() => setLoading(false));

    const es = new EventSource("/api/v1/stream");
    es.onopen = () => setLive(true);
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as FeedEvent;
        if (ev.event_type) setEvents((prev) => [ev, ...prev].slice(0, 120));
      } catch {
        /* heartbeat / non-JSON */
      }
    };
    es.onerror = () => setLive(false);
    return () => es.close();
  }, []);

  // When focused on a fired run, show only that run's events (shared correlation_id).
  const shown = focusId
    ? events.filter((e) => (e.correlation_id ?? e.entity_id) === focusId)
    : events;

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle>Live Pipeline Feed</CardTitle>
          {focusId && (
            <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent ring-1 ring-inset ring-accent/25">
              current run
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {focusId && onShowAll && (
            <button
              onClick={onShowAll}
              className="text-[11px] text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline"
            >
              Show all
            </button>
          )}
          <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
            <span className="relative flex h-2 w-2">
              {live && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />}
              <span className={`relative inline-flex h-2 w-2 rounded-full ${live ? "bg-primary" : "bg-muted-foreground"}`} />
            </span>
            {live ? "streaming live" : "connecting…"}
          </span>
        </div>
      </div>
      <div className="max-h-[24rem] space-y-0.5 overflow-y-auto pr-1">
        {loading ? (
          Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} className="h-9" />)
        ) : !shown.length ? (
          <EmptyState
            title={focusId ? "Waiting for this run…" : "No events yet"}
            hint={focusId ? "Steps will stream in as the agent works" : "Fire an event to see the pipeline react"}
          />
        ) : (
          <AnimatePresence initial={false}>
            {shown.map((a) => {
              const key = `${a.created_at}-${a.event_type}-${seq.current++}`;
              return (
                <motion.div
                  key={key}
                  layout
                  initial={{ opacity: 0, x: -10, backgroundColor: "hsl(258 90% 68% / 0.10)" }}
                  animate={{ opacity: 1, x: 0, backgroundColor: "hsl(258 90% 68% / 0)" }}
                  transition={{ duration: 0.4 }}
                  className="group flex items-center gap-3 rounded-lg px-2.5 py-2 text-xs"
                >
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[a.event_type] ?? "bg-muted-foreground"}`} />
                  <span className="font-mono font-medium text-foreground/90">
                    {a.event_type.replace(/_/g, " ").toLowerCase()}
                  </span>
                  <span className="truncate text-muted-foreground/70">{a.actor}</span>
                  <span className="ml-auto shrink-0 tabular-nums text-[10px] text-muted-foreground/50">
                    {new Date(a.created_at).toLocaleTimeString()}
                  </span>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </Card>
  );
}
