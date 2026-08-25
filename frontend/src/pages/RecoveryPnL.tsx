import { useQuery } from "@tanstack/react-query";
import { ResponsiveSankey } from "@nivo/sankey";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { Card, CardTitle, EmptyState, Skeleton } from "@/components/ui";

const SANKEY_THEME = {
  text: { fill: "hsl(215 20% 62%)", fontSize: 11 },
  tooltip: { container: { background: "hsl(222 40% 8%)", color: "#fff", fontSize: 12, borderRadius: 8 } },
};

function Metric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${tone}`}>{value}</div>
    </div>
  );
}

export default function RecoveryPnL() {
  const pnl = useQuery({ queryKey: ["pnl"], queryFn: api.pnl, refetchInterval: 4000 });
  const sankey = useQuery({ queryKey: ["sankey"], queryFn: api.sankey, refetchInterval: 4000 });

  const rupee = (n?: number) => `₹${(n ?? 0).toLocaleString("en-IN")}`;
  const wf = pnl.data?.by_workflow ?? {};
  const barData = Object.entries(wf).map(([k, v]) => ({ name: k.replace(/_/g, " "), value: v.attributed }));
  const hasSankey = (sankey.data?.links?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Recovery P&L</h1>
        <p className="text-sm text-muted-foreground">
          A true profit &amp; loss for the recovery operation — attributed, not vanity metrics.
        </p>
      </div>

      {pnl.isLoading ? (
        <Skeleton className="h-28" />
      ) : (
        <Card>
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4 lg:grid-cols-6">
            <Metric label="At Risk" value={rupee(pnl.data?.gross_revenue_at_risk)} />
            <Metric label="Recovered" value={rupee(pnl.data?.recovered.attributed)} tone="text-primary" />
            <Metric label="Cost" value={rupee(pnl.data?.cost.total)} tone="text-muted-foreground" />
            <Metric label="Net" value={rupee(pnl.data?.net_recovered)} tone="text-primary" />
            <Metric label="Recovery Rate" value={`${pnl.data?.recovery_rate_pct ?? 0}%`} tone="text-accent" />
            <Metric label="Margin" value={`${pnl.data?.recovery_margin_pct ?? 0}%`} tone="text-accent" />
          </div>
        </Card>
      )}

      <Card>
        <CardTitle>Recovery Flow — ₹ at risk → workflow → outcome</CardTitle>
        <div className="mt-2 h-[24rem]">
          {sankey.isLoading ? (
            <Skeleton className="h-full" />
          ) : hasSankey ? (
            <ResponsiveSankey
              data={sankey.data!}
              margin={{ top: 10, right: 140, bottom: 10, left: 10 }}
              align="justify"
              colors={["#10b981", "#0ea5e9", "#38bdf8", "#f59e0b", "#ef4444", "#64748b"]}
              nodeOpacity={1}
              nodeThickness={16}
              nodeBorderWidth={0}
              linkOpacity={0.35}
              linkHoverOpacity={0.6}
              enableLinkGradient
              labelPosition="outside"
              labelPadding={10}
              theme={SANKEY_THEME}
            />
          ) : (
            <EmptyState title="No flow yet" hint="Recover some cases to populate the Sankey" />
          )}
        </div>
      </Card>

      <Card>
        <CardTitle>Attributed Recovery by Workflow</CardTitle>
        <div className="mt-4 h-56">
          {barData.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                <XAxis dataKey="name" tick={{ fill: "hsl(215 20% 62%)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "hsl(215 20% 62%)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: "hsl(217 33% 14% / 0.5)" }}
                  contentStyle={{ background: "hsl(222 40% 8%)", border: "1px solid hsl(217 33% 16%)", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`₹${v.toLocaleString("en-IN")}`, "attributed"]}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {barData.map((_, i) => <Cell key={i} fill="#10b981" />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No recoveries yet" />
          )}
        </div>
      </Card>
    </div>
  );
}
