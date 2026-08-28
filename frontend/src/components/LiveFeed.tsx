import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "@/lib/api";
import { Card, CardTitle, EmptyState, Skeleton } from "@/components/ui";

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

export function LiveFeed() {
  const { data, isLoading } = useQuery({
    queryKey: ["audit", "feed"],
    queryFn: () => api.audit("?limit=50"),
    refetchInterval: 2000,
  });

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <CardTitle>Live Pipeline Feed</CardTitle>
        <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          streaming
        </span>
      </div>
      <div className="max-h-[24rem] space-y-0.5 overflow-y-auto pr-1">
        {isLoading ? (
          Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} className="h-9" />)
        ) : !data?.length ? (
          <EmptyState title="No events yet" hint="Fire an event to see the pipeline react" />
        ) : (
          <AnimatePresence initial={false}>
            {data.map((a, i) => (
              <motion.div
                key={`${a.created_at}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25 }}
                className="group flex items-center gap-3 rounded-lg px-2.5 py-2 text-xs transition-colors hover:bg-white/[0.03]"
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
            ))}
          </AnimatePresence>
        )}
      </div>
    </Card>
  );
}
