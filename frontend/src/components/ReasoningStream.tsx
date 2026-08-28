import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Brain, Sparkles, Zap } from "lucide-react";
import type { Diagnosis, Intervention } from "@/lib/api";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/utils";

function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = circ * value;
  const tone = value >= 0.8 ? "text-primary" : value >= 0.6 ? "text-warning" : "text-danger";
  const stroke = value >= 0.8 ? "#10b981" : value >= 0.6 ? "#f59e0b" : "#f43f5e";
  return (
    <div className="relative h-[104px] w-[104px] shrink-0">
      <svg viewBox="0 0 88 88" className="h-full w-full -rotate-90">
        <circle cx="44" cy="44" r={r} className="fill-none stroke-white/[0.06]" strokeWidth="6" />
        <motion.circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
          style={{ filter: `drop-shadow(0 0 6px ${stroke}66)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-2xl font-bold tabular-nums", tone)}>{pct}</span>
        <span className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground">
          confidence
        </span>
      </div>
    </div>
  );
}

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
    const step = Math.max(1, Math.round(full.length / 240));
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
            <span className="relative flex h-6 w-6 items-center justify-center rounded-md bg-accent/15">
              <Brain className="h-3.5 w-3.5 text-accent" />
              {!done && (
                <span className="absolute inset-0 animate-ping rounded-md bg-accent/20" />
              )}
            </span>
            Diagnostic Reasoning
            {!done && (
              <span className="flex items-center gap-1 text-[11px] font-normal text-accent">
                <Sparkles className="h-3 w-3 animate-pulse" /> thinking…
              </span>
            )}
          </div>
          <div className="mt-1.5 font-mono text-[11px] text-muted-foreground">
            {diagnosis.llm_model} · prompt v{diagnosis.prompt_version}
          </div>
        </div>
        <ConfidenceGauge value={diagnosis.confidence} />
      </div>

      {/* Terminal-style reasoning panel */}
      <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-[#0a0d14]">
        <div className="flex items-center gap-1.5 border-b border-white/[0.06] px-3 py-2">
          <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-primary/70" />
          <span className="ml-2 font-mono text-[10px] text-muted-foreground">
            chain_of_thought.log
          </span>
        </div>
        <div className="min-h-[7rem] p-4 font-mono text-[13px] leading-relaxed text-foreground/85">
          {shown}
          {!done && (
            <span className="ml-0.5 inline-block h-4 w-[7px] animate-pulse bg-accent align-middle" />
          )}
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: done ? 1 : 0, y: done ? 0 : 10 }}
        transition={{ duration: 0.5 }}
        className="space-y-4"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Root cause</span>
          <Badge label={diagnosis.root_cause_category} tone="in_progress" />
          <span className="text-muted-foreground/40">→</span>
          <span className="text-xs text-muted-foreground">
            recommends {diagnosis.recommended_intervention_class}
          </span>
        </div>

        {intervention && (
          <div className="relative overflow-hidden rounded-xl border border-primary/20 bg-gradient-to-br from-primary/[0.07] to-transparent p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-primary">
              <Zap className="h-4 w-4" />
              Chosen action: {intervention.action_type.replace(/_/g, " ")}
              {intervention.channel && (
                <span className="rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[10px] font-normal uppercase tracking-wide text-muted-foreground">
                  {intervention.channel}
                </span>
              )}
            </div>
            {intervention.message_content && (
              <div className="mt-3 rounded-lg border border-white/[0.06] bg-background/50 p-3">
                <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/60">
                  Generated message
                </div>
                <p className="whitespace-pre-wrap text-sm text-foreground/85">
                  {intervention.message_content}
                </p>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
}
