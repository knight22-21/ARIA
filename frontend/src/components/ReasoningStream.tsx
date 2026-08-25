import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Brain, Zap } from "lucide-react";
import type { Diagnosis, Intervention } from "@/lib/api";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/utils";

function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const r = 34;
  const circ = 2 * Math.PI * r;
  const dash = circ * value;
  const tone = value >= 0.8 ? "text-primary" : value >= 0.6 ? "text-warning" : "text-danger";
  return (
    <div className="relative h-24 w-24">
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
        <circle cx="40" cy="40" r={r} className="fill-none stroke-secondary" strokeWidth="7" />
        <motion.circle
          cx="40"
          cy="40"
          r={r}
          className={cn("fill-none", tone)}
          stroke="currentColor"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-xl font-bold", tone)}>{pct}%</span>
        <span className="text-[9px] uppercase tracking-wider text-muted-foreground">confidence</span>
      </div>
    </div>
  );
}

/** Types out the agent's reasoning like a live stream. */
export function ReasoningStream({
  diagnosis,
  intervention,
}: {
  diagnosis: Diagnosis;
  intervention?: Intervention;
}) {
  const full = diagnosis.reasoning_chain || "";
  const [shown, setShown] = useState("");
  const [done, setDone] = useState(false);
  const idxRef = useRef(0);

  useEffect(() => {
    setShown("");
    setDone(false);
    idxRef.current = 0;
    const step = Math.max(1, Math.round(full.length / 220)); // finish in ~3.5s
    const timer = setInterval(() => {
      idxRef.current += step;
      if (idxRef.current >= full.length) {
        setShown(full);
        setDone(true);
        clearInterval(timer);
      } else {
        setShown(full.slice(0, idxRef.current));
      }
    }, 16);
    return () => clearInterval(timer);
  }, [full]);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Brain className="h-4 w-4 text-accent" /> Diagnostic Reasoning
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {diagnosis.llm_model} · prompt v{diagnosis.prompt_version}
          </div>
        </div>
        <ConfidenceGauge value={diagnosis.confidence} />
      </div>

      <div className="rounded-lg border border-border/60 bg-background/40 p-4 font-mono text-[13px] leading-relaxed text-foreground/90">
        {shown}
        {!done && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-accent align-middle" />}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: done ? 1 : 0, y: done ? 0 : 8 }}
        transition={{ duration: 0.4 }}
        className="space-y-4"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Root cause</span>
          <Badge label={diagnosis.root_cause_category} tone="in_progress" />
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">
            recommends {diagnosis.recommended_intervention_class}
          </span>
        </div>

        {intervention && (
          <div className="rounded-lg border border-primary/25 bg-primary/5 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-primary">
              <Zap className="h-4 w-4" /> Chosen action: {intervention.action_type.replace(/_/g, " ")}
              {intervention.channel && (
                <span className="text-xs font-normal text-muted-foreground">
                  via {intervention.channel}
                </span>
              )}
            </div>
            {intervention.message_content && (
              <p className="mt-2 whitespace-pre-wrap text-sm text-foreground/80">
                {intervention.message_content}
              </p>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
}
