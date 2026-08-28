import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { EmptyState, PageHeader, Select, Skeleton } from "@/components/ui";

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
      <PageHeader
        title="Audit Ledger"
        subtitle="Append-only and tamper-evident. Every decision and action, with a SHA-256 checksum."
        actions={
          <Select value={type} onChange={setType}>
            <option value="">All events</option>
            {types.map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
        }
      />

      <div className="card-elevated overflow-hidden">
        {isLoading ? (
          <div className="space-y-2 p-5">{Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-7" />)}</div>
        ) : !data?.length ? (
          <div className="p-6"><EmptyState title="No audit events" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                <th className="px-5 py-3 font-medium">Event</th>
                <th className="px-5 py-3 font-medium">Actor</th>
                <th className="px-5 py-3 font-medium">Entity</th>
                <th className="px-5 py-3 font-medium">Checksum</th>
                <th className="px-5 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.audit_id} className="border-b border-white/[0.04] transition-colors last:border-0 hover:bg-white/[0.025]">
                  <td className="px-5 py-2.5 font-mono text-xs font-medium text-foreground/90">{a.event_type}</td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">{a.actor}</td>
                  <td className="px-5 py-2.5 text-xs text-muted-foreground">{a.entity_type}</td>
                  <td className="px-5 py-2.5">
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-primary/[0.08] px-2 py-0.5 font-mono text-[11px] text-primary/90">
                      <ShieldCheck className="h-3 w-3" /> {a.checksum}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 tabular-nums text-[11px] text-muted-foreground">{new Date(a.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
