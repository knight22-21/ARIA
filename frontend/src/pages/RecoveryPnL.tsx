import { useQuery } from "@tanstack/react-query";
import { ResponsiveSankey } from "@nivo/sankey";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { Card, CardTitle, EmptyState, PageHeader, Skeleton } from "@/components/ui";

const SANKEY_THEME = {
  text: { fill: "hsl(218 12% 56%)", fontSize: 11, fontFamily: "Inter, sans-serif" },
  tooltip: {
    container: {
      background: "hsl(224 20% 9%)",
      color: "#fff",
      fontSize: 12,
      borderRadius: 10,
      border: "1px solid hsl(220 14% 16%)",
    },
  },
};
// Brighter, higher-saturation palette so nodes/links read on the dark canvas.
const SANKEY_COLORS = ["#34d399", "#a78bfa", "#38bdf8", "#22d3ee", "#fbbf24", "#fb7185", "#94a3b8"];

function Metric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground">{label}</div>
      <div className={`mt-1.5 text-2xl font-bold tabular-nums ${tone}`}>{value}</div>
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
      <PageHeader
        title="Recovery P&L"
        subtitle="A true profit & loss for the recovery operation — attributed, not vanity metrics."
      />

      {pnl.isLoading ? (
        <Skeleton className="h-28 rounded-2xl" />
      ) : (
        <Card>
          <div className="grid grid-cols-2 gap-6 md:grid-cols-3 lg:grid-cols-6">
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
        <CardTitle>Recovery Flow · ₹ at risk → workflow → outcome</CardTitle>
        <div className="mt-3 h-[24rem]">
          {sankey.isLoading ? (
            <Skeleton className="h-full rounded-xl" />
          ) : hasSankey ? (
            <ResponsiveSankey
              data={sankey.data!}
              margin={{ top: 12, right: 150, bottom: 12, left: 12 }}
              align="justify"
              colors={SANKEY_COLORS}
              nodeOpacity={1}
              nodeThickness={18}
              nodeBorderWidth={0}
              nodeBorderRadius={3}
              linkOpacity={0.55}
              linkHoverOpacity={0.85}
              linkBlendMode="normal"
              enableLinkGradient
              labelPosition="outside"
              labelPadding={12}
              labelTextColor="hsl(210 22% 96%)"
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
                <XAxis dataKey="name" tick={{ fill: "hsl(218 12% 56%)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "hsl(218 12% 56%)", fontSize: 11 }} axisLine={false} tickLine={false} width={70} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  cursor={{ fill: "hsl(220 16% 13% / 0.4)" }}
                  contentStyle={{ background: "hsl(224 20% 9%)", border: "1px solid hsl(220 14% 16%)", borderRadius: 10, fontSize: 12 }}
                  formatter={(v: number) => [`₹${v.toLocaleString("en-IN")}`, "attributed"]}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {barData.map((_, i) => <Cell key={i} fill="url(#barGrad)" />)}
                </Bar>
                <defs>
                  <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#34d399" />
                    <stop offset="100%" stopColor="#059669" stopOpacity={0.7} />
                  </linearGradient>
                </defs>
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
