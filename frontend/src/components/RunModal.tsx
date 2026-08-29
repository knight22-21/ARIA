import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Loader2, X, ExternalLink, Copy, CheckCircle2, Sparkles } from "lucide-react";
import { formatINR } from "@/lib/utils";
import type { RunResult } from "@/lib/api";
import { Button } from "@/components/ui";

interface StreamEvent {
  event_type: string;
  actor: string;
  created_at: string;
  correlation_id?: string | null;
}

const STEP_META: Record<string, { label: string; hint: string; tone: string }> = {
  RISK_DETECTED: { label: "Risk detected", hint: "multi-signal scoring", tone: "text-info" },
  POLICY_CHECKED: { label: "Policy checked", hint: "stopping rules & compliance", tone: "text-muted-foreground" },
  STOPPING_RULE_FIRED: { label: "Stopping rule fired", hint: "suppressed", tone: "text-danger" },
  DIAGNOSIS_PRODUCED: { label: "Diagnosed", hint: "LLM root-cause reasoning", tone: "text-accent" },
  INTERVENTION_PLANNED: { label: "Intervention chosen", hint: "bounded action space", tone: "text-accent" },
  ACTION_EXECUTED: { label: "Action executed", hint: "recovery workflow", tone: "text-primary" },
  ESCALATION_RAISED: { label: "Escalated to human", hint: "review queue", tone: "text-warning" },
  AGENT_DECISION: { label: "Decision finalized", hint: "", tone: "text-muted-foreground" },
  OUTCOME_DETECTED: { label: "Payment detected", hint: "real capture", tone: "text-primary" },
  RECOVERY_ATTRIBUTED: { label: "Recovery attributed", hint: "money recovered", tone: "text-primary" },
};

export function RunModal({
  open,
  onClose,
  mode,
  scenario,
  trigger,
}: {
  open: boolean;
  onClose: () => void;
  mode: "inject" | "recover";
  scenario: string;
  trigger: () => Promise<RunResult>;
}) {
  const [steps, setSteps] = useState<StreamEvent[]>([]);
  const [result, setResult] = useState<RunResult | null>(null);
  const [recovered, setRecovered] = useState(false);
  const [running, setRunning] = useState(false);
  const [copied, setCopied] = useState(false);
  const corrRef = useRef<string | null>(null);
  const amountRef = useRef<number>(0);
  const startedRef = useRef(false);

  // Live stream — recreated per effect invoke; only one connection is ever active.
  useEffect(() => {
    if (!open) return;
    const es = new EventSource("/api/v1/stream");
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as StreamEvent;
        if (!ev.event_type) return;
        if (corrRef.current && ev.correlation_id && ev.correlation_id !== corrRef.current) return;
        setSteps((prev) =>
          prev.some((p) => p.event_type === ev.event_type && p.created_at === ev.created_at)
            ? prev
            : [...prev, ev],
        );
        if (ev.event_type === "RECOVERY_ATTRIBUTED") setRecovered(true);
      } catch {
        /* heartbeat */
      }
    };
    return () => es.close();
  }, [open]);

  // Kick off the run EXACTLY once (guards against React StrictMode's double-invoke,
  // which was otherwise firing the pipeline twice → duplicate events).
  useEffect(() => {
    if (!open || startedRef.current) return;
    startedRef.current = true;
    setSteps([]);
    setResult(null);
    setRecovered(false);
    setRunning(true);
    corrRef.current = null;
    amountRef.current = 0;
    trigger()
      .then((r) => {
        corrRef.current = r.risk_event_id ?? null;
        amountRef.current = r.amount_paise ?? 0;
        setResult(r);
      })
      .catch(() => {})
      .finally(() => setRunning(false));
  }, [open, trigger]);

  if (!open) return null;

  const copy = () => {
    if (result?.payment_link_url) {
      navigator.clipboard.writeText(result.payment_link_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const title =
    mode === "recover" ? "Live Recovery — real Razorpay link" : "Live Pipeline Run";

  return createPortal(
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[100] grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="card-elevated w-full max-w-lg overflow-hidden p-0"
          initial={{ opacity: 0, y: 16, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              <div>
                <div className="text-sm font-semibold">{title}</div>
                <div className="text-[11px] text-muted-foreground">{scenario.replace(/_/g, " ")}</div>
              </div>
            </div>
            <button onClick={onClose} className="rounded-lg p-1.5 text-muted-foreground hover:bg-white/[0.05] hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="max-h-[70vh] overflow-y-auto px-5 py-5">
            {/* Sequential stepper */}
            <ol className="relative ml-1 space-y-1 border-l border-white/[0.08] pl-6">
              <AnimatePresence initial={false}>
                {steps.map((s, i) => {
                  const meta = STEP_META[s.event_type] ?? { label: s.event_type, hint: "", tone: "text-muted-foreground" };
                  const isLast = i === steps.length - 1;
                  const stillRunning = running && isLast;
                  return (
                    <motion.li
                      key={`${s.event_type}-${s.created_at}`}
                      initial={{ opacity: 0, x: -8, height: 0 }}
                      animate={{ opacity: 1, x: 0, height: "auto" }}
                      transition={{ duration: 0.3 }}
                      className="relative py-2"
                    >
                      <span className="absolute -left-[31px] top-2.5 grid h-5 w-5 place-items-center rounded-full bg-card ring-4 ring-card">
                        {stillRunning ? (
                          <Loader2 className={`h-4 w-4 animate-spin ${meta.tone}`} />
                        ) : (
                          <span className={`grid h-4 w-4 place-items-center rounded-full bg-white/[0.06] ${meta.tone}`}>
                            <Check className="h-2.5 w-2.5" />
                          </span>
                        )}
                      </span>
                      <div className={`text-sm font-medium ${meta.tone}`}>{meta.label}</div>
                      {meta.hint && <div className="text-[11px] text-muted-foreground">{meta.hint}</div>}
                    </motion.li>
                  );
                })}
              </AnimatePresence>
              {running && steps.length === 0 && (
                <li className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Starting run…
                </li>
              )}
            </ol>

            {/* Diagnosis chip */}
            {result?.diagnosis && (
              <div className="mt-4 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs">
                <span className="text-muted-foreground">Root cause · </span>
                <span className="font-medium text-accent">{result.diagnosis.root_cause_category}</span>
                <span className="text-muted-foreground"> ({Math.round(result.diagnosis.confidence * 100)}% conf)</span>
              </div>
            )}

            {/* Recover mode: payment link → recovered */}
            {mode === "recover" && result?.payment_link_url && !recovered && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 rounded-xl border border-primary/25 bg-primary/[0.06] p-4"
              >
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                  </span>
                  Real payment link ready — awaiting payment
                </div>
                <div className="flex items-center gap-2">
                  <a href={result.payment_link_url} target="_blank" rel="noreferrer" className="flex-1">
                    <Button className="w-full">
                      <ExternalLink className="h-4 w-4" /> Open & pay {formatINR(result.amount_paise ?? 0)}
                    </Button>
                  </a>
                  <Button variant="outline" onClick={copy} title="Copy link">
                    {copied ? <Check className="h-4 w-4 text-primary" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <div className="mt-2 truncate text-[10px] text-muted-foreground">{result.payment_link_url}</div>
              </motion.div>
            )}

            {recovered && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 15 }}
                className="mt-4 flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/[0.1] p-4"
              >
                <CheckCircle2 className="h-8 w-8 text-primary" />
                <div>
                  <div className="text-lg font-bold text-primary">
                    Recovered {formatINR(amountRef.current)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Real Razorpay payment attributed · P&L updated
                  </div>
                </div>
              </motion.div>
            )}

            {/* Inject mode: outcome summary */}
            {mode === "inject" && !running && result && (
              <div className="mt-4 space-y-2 text-sm">
                {result.outcome && (
                  <div>
                    <span className="text-muted-foreground">Outcome · </span>
                    <span className="font-medium capitalize">{result.outcome}</span>
                  </div>
                )}
                {result.intervention && (
                  <div className="text-muted-foreground">
                    Action · <span className="text-foreground">{result.intervention.action_type.replace(/_/g, " ")}</span>
                    {result.intervention.channel && <span> via {result.intervention.channel}</span>}
                  </div>
                )}
                {result.escalation && (
                  <div className="text-warning">Escalated ({result.escalation.urgency}) — {result.escalation.reason}</div>
                )}
              </div>
            )}
          </div>

          <div className="flex justify-end border-t border-white/[0.06] px-5 py-3">
            <Button variant="ghost" onClick={onClose}>Close</Button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body,
  );
}
