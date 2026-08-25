import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { EmptyState, Skeleton } from "@/components/ui";

export default function AuditLedger() {
  const [type, setType] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["audit", "ledger", type],
    queryFn: () => api.audit(`?limit=200${type ? `&event_type=${type}` : ""}`),
    refetchInterval: 3000,
  });

  const types = Array.from(new Set((data ?? []).map((a) => a.event_type))).sort();

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Ledger</h1>
          <p className="text-sm text-muted-foreground">
            Append-only, tamper-evident. Every decision and action, with a SHA-256 checksum.
          </p>
        </div>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="rounded-lg border border-border bg-background/60 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50"
        >
          <option value="">All events</option>
          {types.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="glass overflow-hidden rounded-xl">
        {isLoading ? (
          <div className="space-y-2 p-5">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-6" />)}</div>
        ) : !data?.length ? (
          <div className="p-6"><EmptyState title="No audit events" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/60 text-left text-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-5 py-3 font-medium">Event</th>
                <th className="px-5 py-3 font-medium">Actor</th>
                <th className="px-5 py-3 font-medium">Entity</th>
                <th className="px-5 py-3 font-medium">Checksum</th>
                <th className="px-5 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.audit_id} className="border-b border-border/40 hover:bg-secondary/40">
                  <td className="px-5 py-2.5 font-mono text-xs text-foreground/90">{a.event_type}</td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">{a.actor}</td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">{a.entity_type}</td>
                  <td className="px-5 py-2.5">
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] text-primary/80">
                      <ShieldCheck className="h-3 w-3" /> {a.checksum}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-[11px] text-muted-foreground">{new Date(a.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
