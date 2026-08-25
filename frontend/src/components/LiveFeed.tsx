import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "@/lib/api";
import { EmptyState, Skeleton } from "@/components/ui";

const DOT: Record<string, string> = {
  RISK_DETECTED: "bg-info",
  DIAGNOSIS_PRODUCED: "bg-accent",
  INTERVENTION_PLANNED: "bg-accent",
  ACTION_EXECUTED: "bg-primary",
  ESCALATION_RAISED: "bg-warning",
  STOPPING_RULE_FIRED: "bg-danger",
  RECOVERY_ATTRIBUTED: "bg-primary",
  HUMAN_APPROVED: "bg-primary",
  HUMAN_REJECTED: "bg-danger",
};

export function LiveFeed() {
  const { data, isLoading } = useQuery({
    queryKey: ["audit", "feed"],
    queryFn: () => api.audit("?limit=40"),
    refetchInterval: 2000,
  });

  return (
    <div className="glass rounded-xl p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-semibold">Live Pipeline Feed</div>
        <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-primary" /> streaming
        </span>
      </div>
      <div className="max-h-[26rem] space-y-1 overflow-y-auto pr-1">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-8" />)
        ) : !data?.length ? (
          <EmptyState title="No events yet" hint="Fire an event to see the pipeline react" />
        ) : (
          <AnimatePresence initial={false}>
            {data.map((a, i) => (
              <motion.div
                key={`${a.created_at}-${i}`}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-3 rounded-lg px-2 py-1.5 text-xs hover:bg-secondary/50"
              >
                <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[a.event_type] ?? "bg-muted-foreground"}`} />
                <span className="font-mono text-foreground/90">{a.event_type}</span>
                <span className="truncate text-muted-foreground">{a.actor}</span>
                <span className="ml-auto shrink-0 text-[10px] text-muted-foreground/70">
                  {new Date(a.created_at).toLocaleTimeString()}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
