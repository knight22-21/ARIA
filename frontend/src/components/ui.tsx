import { cn } from "@/lib/utils";
import type { ReactNode, ButtonHTMLAttributes } from "react";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("glass rounded-xl p-5", className)}>{children}</div>;
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("text-xs font-medium uppercase tracking-wider text-muted-foreground", className)}>
      {children}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  detected: "bg-info/15 text-info border-info/30",
  in_progress: "bg-accent/15 text-accent border-accent/30",
  recovered: "bg-primary/15 text-primary border-primary/30",
  unrecovered: "bg-muted text-muted-foreground border-border",
  escalated: "bg-warning/15 text-warning border-warning/30",
  suppressed: "bg-danger/15 text-danger border-danger/30",
  P1: "bg-danger/15 text-danger border-danger/30",
  P2: "bg-warning/15 text-warning border-warning/30",
  P3: "bg-info/15 text-info border-info/30",
};

export function Badge({ label, tone }: { label: string; tone?: string }) {
  const style = STATUS_STYLES[tone ?? label] ?? "bg-secondary text-secondary-foreground border-border";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        style,
      )}
    >
      {label.replace(/_/g, " ")}
    </span>
  );
}

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger" | "outline";
}

export function Button({ variant = "primary", className, children, ...props }: BtnProps) {
  const variants = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    ghost: "hover:bg-secondary text-foreground",
    outline: "border border-border hover:bg-secondary text-foreground",
    danger: "bg-danger/90 text-white hover:bg-danger",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium",
        "transition-colors focus:outline-none focus:ring-2 focus:ring-ring/50 disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton h-4 w-full", className)} />;
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16 text-center">
      <div className="text-sm font-medium text-muted-foreground">{title}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground/70">{hint}</div>}
    </div>
  );
}
