import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Card, CardTitle, EmptyState, Skeleton } from "@/components/ui";
import { ReasoningStream } from "@/components/ReasoningStream";
import { AuditTimeline } from "@/components/AuditTimeline";
import { formatINR } from "@/lib/utils";

export default function RiskDetail() {
  const { id = "" } = useParams();
  const { data, isLoading } = useQuery({ queryKey: ["trail", id], queryFn: () => api.trail(id) });

  return (
    <div className="space-y-6">
      <Link
        to="/risk"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Risk Events
      </Link>

      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-96 rounded-2xl lg:col-span-2" />
          <Skeleton className="h-96 rounded-2xl" />
        </div>
      ) : !data ? (
        <EmptyState title="Not found" />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold capitalize tracking-tight">
              {data.risk_event.workflow_type.replace(/_/g, " ")}
            </h1>
            <Badge label={data.risk_event.status} tone={data.risk_event.status} />
            <span className="text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">
                {formatINR(data.risk_event.amount_at_risk_paise)}
              </span>{" "}
              at risk · risk score {data.risk_event.risk_score.toFixed(2)}
            </span>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card className="h-full">
                {data.diagnosis ? (
                  <ReasoningStream diagnosis={data.diagnosis} intervention={data.interventions[0]} />
                ) : (
                  <EmptyState
                    title="No diagnosis"
                    hint="This case was gated by a stopping rule before diagnosis."
                  />
                )}
              </Card>
            </div>

            <Card className="h-full">
              <CardTitle>Audit Lifecycle</CardTitle>
              <div className="mt-5">
                <AuditTimeline items={data.audit} />
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
