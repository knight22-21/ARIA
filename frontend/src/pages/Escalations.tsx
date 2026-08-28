import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { api, type Escalation } from "@/lib/api";
import { Badge, Button, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { formatINR } from "@/lib/utils";

function EscalationCard({ e }: { e: Escalation }) {
  const qc = useQueryClient();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");

  const refresh = () =>
    ["escalations", "summary", "pnl", "risk-events", "audit"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k] }),
    );

  const approve = useMutation({
    mutationFn: () => api.approve(e.risk_event_id),
    onSuccess: () => {
      toast.success("Approved — action queued for execution");
      refresh();
    },
    onError: (err: Error) => toast.error("Approve failed", { description: err.message }),
  });

  const reject = useMutation({
    mutationFn: () => api.reject(e.risk_event_id, reason),
    onSuccess: () => {
      toast("Rejected", { description: reason });
      refresh();
    },
    onError: (err: Error) => toast.error("Reject failed", { description: err.message }),
  });

  return (
    <motion.div layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.97 }}>
      <Card className="h-full">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            {e.urgency && <Badge label={e.urgency} tone={e.urgency} />}
            <span className="font-medium capitalize">{e.workflow_type.replace(/_/g, " ")}</span>
          </div>
          <span className="text-lg font-bold tabular-nums">{formatINR(e.amount_at_risk_paise)}</span>
        </div>

        <p className="mt-3 text-sm leading-relaxed text-foreground/80">{e.summary}</p>
        {e.recommended_action && (
          <div className="mt-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-xs leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground/70">Recommended · </span>
            {e.recommended_action}
          </div>
        )}

        {rejecting ? (
          <div className="mt-4 space-y-2">
            <input
              autoFocus
              value={reason}
              onChange={(ev) => setReason(ev.target.value)}
              placeholder="Reason for rejection (required)"
              className="ring-focus w-full rounded-lg border border-border bg-white/[0.02] px-3 py-2 text-sm"
            />
            <div className="flex gap-2">
              <Button variant="danger" onClick={() => reject.mutate()} disabled={!reason.trim() || reject.isPending}>
                {reject.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
                Confirm reject
              </Button>
              <Button variant="ghost" onClick={() => setRejecting(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="mt-4 flex gap-2">
            <Button onClick={() => approve.mutate()} disabled={approve.isPending}>
              {approve.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Approve
            </Button>
            <Button variant="outline" onClick={() => setRejecting(true)}>
              <X className="h-4 w-4" /> Reject
            </Button>
          </div>
        )}
      </Card>
    </motion.div>
  );
}

export default function Escalations() {
  const { data, isLoading } = useQuery({
    queryKey: ["escalations"],
    queryFn: api.escalations,
    refetchInterval: 4000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Action Queue"
        subtitle="Cases ARIA escalated for human review. Approve to let ARIA act, or reject with a reason."
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-52 rounded-2xl" />)}
        </div>
      ) : !data?.length ? (
        <EmptyState title="Queue is clear" hint="No cases awaiting human review." icon={<ShieldCheck className="h-8 w-8" />} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <AnimatePresence>
            {data.map((e) => <EscalationCard key={e.risk_event_id} e={e} />)}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
