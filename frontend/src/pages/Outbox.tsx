import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { EmptyState, Skeleton } from "@/components/ui";
import { MessageCard } from "@/components/MessageCard";

export default function Outbox() {
  const { data, isLoading } = useQuery({
    queryKey: ["outbox"],
    queryFn: api.outbox,
    refetchInterval: 4000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Outbox</h1>
        <p className="text-sm text-muted-foreground">
          Messages ARIA generated (WhatsApp / SMS / email / Hinglish voice) — rendered, not sent.
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-40" />)}
        </div>
      ) : !data?.length ? (
        <EmptyState title="Outbox is empty" hint="Interventions that send messages will appear here" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((m) => <MessageCard key={m.outbox_id} msg={m} />)}
        </div>
      )}
    </div>
  );
}
