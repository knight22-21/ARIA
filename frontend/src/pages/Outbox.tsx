import { useQuery } from "@tanstack/react-query";
import { Inbox } from "lucide-react";
import { api } from "@/lib/api";
import { EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { MessageCard } from "@/components/MessageCard";

export default function Outbox() {
  const { data, isLoading } = useQuery({
    queryKey: ["outbox"],
    queryFn: api.outbox,
    refetchInterval: 4000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Outbox"
        subtitle="Messages ARIA generated (WhatsApp · SMS · email · Hinglish voice) — rendered, never sent."
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-44 rounded-2xl" />)}
        </div>
      ) : !data?.length ? (
        <EmptyState title="Outbox is empty" hint="Interventions that send messages appear here" icon={<Inbox className="h-8 w-8" />} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((m) => <MessageCard key={m.outbox_id} msg={m} />)}
        </div>
      )}
    </div>
  );
}
