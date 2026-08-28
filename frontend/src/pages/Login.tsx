import { useState } from "react";
import { motion } from "framer-motion";
import { Lock, User, ArrowRight } from "lucide-react";
import { login } from "@/lib/auth";
import { Button } from "@/components/ui";

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (login(username, password)) {
      onSuccess();
    } else {
      setError("Invalid credentials. Try again.");
    }
  };

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-sm"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent text-2xl font-bold text-background shadow-[0_8px_28px_-6px_hsl(258_90%_60%/0.6)]">
            A
          </div>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight">Sign in to ARIA</h1>
          <p className="mt-1 text-sm text-muted-foreground">Autonomous Revenue Intelligence</p>
        </div>

        <form onSubmit={submit} className="card-elevated space-y-4 p-6">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Username</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="ring-focus w-full rounded-lg border border-border bg-white/[0.02] py-2.5 pl-9 pr-3 text-sm transition-colors hover:border-white/[0.12]"
              />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="ring-focus w-full rounded-lg border border-border bg-white/[0.02] py-2.5 pl-9 pr-3 text-sm transition-colors hover:border-white/[0.12]"
              />
            </div>
          </div>

          {error && <div className="text-xs text-danger">{error}</div>}

          <Button type="submit" className="w-full">
            Sign in <ArrowRight className="h-4 w-4" />
          </Button>

          <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-center text-[11px] text-muted-foreground">
            Demo credentials · <span className="font-mono text-foreground/80">admin</span> /{" "}
            <span className="font-mono text-foreground/80">aria2026</span>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
