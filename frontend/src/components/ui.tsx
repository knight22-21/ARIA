import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import type { ReactNode, ButtonHTMLAttributes } from "react";

export function Card({
  className,
  children,
  hover = false,
}: {
  className?: string;
  children: ReactNode;
  hover?: boolean;
}) {
  return (
    <div
      className={cn(
        "card-elevated p-5 transition-all duration-300",
        hover && "hover:-translate-y-0.5 hover:border-white/[0.10]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </motion.div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// [chip classes, dot class] — static so Tailwind's JIT keeps them.
const STATUS_STYLES: Record<string, [string, string]> = {
  detected: ["bg-info/10 text-info ring-info/25", "bg-info"],
  in_progress: ["bg-accent/10 text-accent ring-accent/25", "bg-accent"],
  recovered: ["bg-primary/10 text-primary ring-primary/25", "bg-primary"],
  unrecovered: ["bg-muted text-muted-foreground ring-border", "bg-muted-foreground"],
  escalated: ["bg-warning/10 text-warning ring-warning/25", "bg-warning"],
  suppressed: ["bg-danger/10 text-danger ring-danger/25", "bg-danger"],
  P1: ["bg-danger/10 text-danger ring-danger/25", "bg-danger"],
  P2: ["bg-warning/10 text-warning ring-warning/25", "bg-warning"],
  P3: ["bg-info/10 text-info ring-info/25", "bg-info"],
};

export function Badge({ label, tone }: { label: string; tone?: string }) {
  const [style, dot] = STATUS_STYLES[tone ?? label] ?? [
    "bg-secondary text-secondary-foreground ring-border",
    "bg-muted-foreground",
  ];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        style,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {label.replace(/_/g, " ")}
    </span>
  );
}

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md";
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: BtnProps) {
  const variants = {
    primary:
      "bg-primary text-primary-foreground shadow-[0_1px_0_0_hsl(0_0%_100%/0.15)_inset,0_4px_12px_-4px_hsl(152_72%_45%/0.5)] hover:bg-primary/90",
    ghost: "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground",
    outline: "border border-border bg-white/[0.02] text-foreground hover:bg-white/[0.05] hover:border-white/[0.12]",
    danger: "bg-danger/90 text-white hover:bg-danger shadow-[0_4px_12px_-4px_hsl(351_83%_61%/0.5)]",
  };
  const sizes = { sm: "px-2.5 py-1.5 text-xs", md: "px-3.5 py-2 text-sm" };
  return (
    <button
      className={cn(
        "ring-focus inline-flex items-center justify-center gap-2 rounded-lg font-medium",
        "transition-all duration-200 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
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

export function EmptyState({ title, hint, icon }: { title: string; hint?: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border/70 py-16 text-center">
      {icon && <div className="mb-3 text-muted-foreground/50">{icon}</div>}
      <div className="text-sm font-medium text-muted-foreground">{title}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground/60">{hint}</div>}
    </div>
  );
}

export function Select({
  value,
  onChange,
  children,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "ring-focus rounded-lg border border-border bg-white/[0.02] px-3 py-2 text-sm text-foreground transition-colors hover:border-white/[0.12]",
        className,
      )}
    >
      {children}
    </select>
  );
}
