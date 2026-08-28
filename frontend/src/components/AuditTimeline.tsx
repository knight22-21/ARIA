import { motion } from "framer-motion";
import type { AuditItem } from "@/lib/api";

const DOT: Record<string, string> = {
  RISK_DETECTED: "bg-info",
  POLICY_CHECKED: "bg-muted-foreground",
  STOPPING_RULE_FIRED: "bg-danger",
  DIAGNOSIS_PRODUCED: "bg-accent",
  INTERVENTION_PLANNED: "bg-accent",
  ACTION_EXECUTED: "bg-primary",
  AGENT_DECISION: "bg-muted-foreground",
  ESCALATION_RAISED: "bg-warning",
  HUMAN_APPROVED: "bg-primary",
  HUMAN_REJECTED: "bg-danger",
  OUTCOME_DETECTED: "bg-primary",
  RECOVERY_ATTRIBUTED: "bg-primary",
};

export function AuditTimeline({ items }: { items: AuditItem[] }) {
  return (
    <ol className="relative ml-1.5 space-y-5 border-l border-white/[0.08] pl-6">
      {items.map((a, i) => {
        const color = DOT[a.event_type] ?? "bg-muted-foreground";
        return (
          <motion.li
            key={i}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06 }}
            className="relative"
          >
            <span className={`absolute -left-[30px] top-0.5 h-3 w-3 rounded-full ring-4 ring-card ${color}`}>
              <span className={`absolute inset-0 rounded-full ${color} opacity-40 blur-[3px]`} />
            </span>
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-mono text-xs font-medium text-foreground">{a.event_type}</span>
              <span className="shrink-0 tabular-nums text-[10px] text-muted-foreground/60">
                {new Date(a.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="mt-0.5 text-[11px] text-muted-foreground/70">{a.actor}</div>
          </motion.li>
        );
      })}
    </ol>
  );
}
