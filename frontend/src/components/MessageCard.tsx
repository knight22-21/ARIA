import { Mail, MessageCircle, Phone, Smartphone } from "lucide-react";
import type { OutboxMsg } from "@/lib/api";
import { cn, formatINR } from "@/lib/utils";

const CHANNEL = {
  whatsapp: { icon: MessageCircle, color: "text-[#25D366]", label: "WhatsApp", bubble: "bg-[#25D366]/10 border-[#25D366]/20" },
  sms: { icon: Smartphone, color: "text-info", label: "SMS", bubble: "bg-info/10 border-info/20" },
  email: { icon: Mail, color: "text-accent", label: "Email", bubble: "bg-accent/10 border-accent/20" },
  ivr: { icon: Phone, color: "text-warning", label: "Voice / IVR", bubble: "bg-warning/10 border-warning/20" },
  internal_retry: { icon: Smartphone, color: "text-muted-foreground", label: "Internal", bubble: "bg-secondary border-border" },
} as const;

export function MessageCard({ msg }: { msg: OutboxMsg }) {
  const c = CHANNEL[msg.channel as keyof typeof CHANNEL] ?? CHANNEL.internal_retry;
  const Icon = c.icon;
  return (
    <div className="glass rounded-xl p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className={cn("flex items-center gap-2 text-xs font-medium", c.color)}>
          <Icon className="h-4 w-4" /> {c.label}
        </div>
        <span className="text-[10px] text-muted-foreground">
          {msg.recipient ?? "—"} · {msg.status}
        </span>
      </div>
      <div className={cn("rounded-lg border p-3 text-sm text-foreground/90", c.bubble)}>
        {msg.subject && <div className="mb-1 font-medium">{msg.subject}</div>}
        <p className="whitespace-pre-wrap">{msg.body || "(no content)"}</p>
      </div>
      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
        <span>{new Date(msg.created_at).toLocaleString()}</span>
        <span>cost {formatINR(msg.cost_paise)}</span>
      </div>
    </div>
  );
}
