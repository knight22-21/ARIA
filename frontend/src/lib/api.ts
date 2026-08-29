// Typed API client. All calls go through the Vite dev proxy at /api → FastAPI.

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${r.status} ${r.statusText}: ${text.slice(0, 200)}`);
  }
  return r.json() as Promise<T>;
}

// ---- Types ----
export type RiskStatus =
  | "detected"
  | "in_progress"
  | "recovered"
  | "unrecovered"
  | "escalated"
  | "suppressed";

export interface RiskEvent {
  risk_event_id: string;
  payment_event_id: string | null;
  merchant_id: string;
  risk_score: number;
  risk_signals: { signal_type: string; value: number; weight: number }[];
  workflow_type: string;
  status: RiskStatus;
  amount_at_risk_paise: number;
  detected_at: string;
  resolved_at: string | null;
}

export interface Diagnosis {
  root_cause_category: string;
  confidence: number;
  reasoning_chain: string;
  recommended_intervention_class: string;
  urgency_score: number;
  llm_model: string;
  prompt_version: string;
}

export interface Intervention {
  action_type: string;
  channel: string | null;
  message_content: string | null;
  scheduled_at: string | null;
  estimated_cost_paise: number;
  status: string;
}

export interface AuditItem {
  event_type: string;
  actor: string;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface AuditRow extends AuditItem {
  audit_id: string;
  entity_type: string | null;
  entity_id: string | null;
  checksum: string;
}

export interface Trail {
  risk_event: { status: string; workflow_type: string; risk_score: number; amount_at_risk_paise: number };
  diagnosis: Diagnosis | null;
  interventions: Intervention[];
  audit: AuditItem[];
}

export interface Summary {
  total_events: number;
  total_at_risk_paise: number;
  by_status: Record<string, { count: number; amount_paise: number }>;
  outbox_count: number;
}

export interface PnL {
  gross_revenue_at_risk: number;
  interventions: { auto: number; escalated: number };
  recovered: { direct: number; assisted: number; gross: number; attributed: number };
  cost: { total: number };
  net_recovered: number;
  recovery_rate_pct: number;
  recovery_margin_pct: number;
  cost_per_rupee_recovered: number;
  by_workflow: Record<string, { recovered: number; attributed: number; count: number }>;
}

export interface Escalation {
  risk_event_id: string;
  workflow_type: string;
  amount_at_risk_paise: number;
  urgency: string | null;
  summary: string | null;
  recommended_action: string | null;
  reason: string | null;
}

export interface OutboxMsg {
  outbox_id: string;
  channel: string;
  recipient: string | null;
  subject: string | null;
  body: string | null;
  status: string;
  cost_paise: number;
  created_at: string;
}

export interface SankeyData {
  nodes: { id: string }[];
  links: { source: string; target: string; value: number }[];
}

export interface InjectResult {
  risk_event_id: string | null;
  outcome?: string;
  workflow_type?: string;
  diagnosis?: { root_cause_category: string; confidence: number };
  intervention?: { action_type: string; channel: string | null; message_preview: string };
  escalation?: { urgency: string; reason: string };
}

export interface RecoverResult {
  risk_event_id: string;
  amount_paise: number;
  workflow_type: string;
  diagnosis: { root_cause_category: string; confidence: number };
  payment_link_url: string | null;
  message: string;
}

/** Superset returned by either inject or recover — consumed by the run modal. */
export interface RunResult {
  risk_event_id?: string | null;
  amount_paise?: number;
  outcome?: string;
  workflow_type?: string;
  diagnosis?: { root_cause_category: string; confidence: number };
  intervention?: { action_type: string; channel: string | null; message_preview?: string };
  escalation?: { urgency: string; reason: string };
  payment_link_url?: string | null;
  message?: string;
}

// ---- Calls ----
export const api = {
  summary: () => req<Summary>("/v1/stats/summary"),
  riskEvents: (q = "") => req<RiskEvent[]>(`/v1/risk-events${q}`),
  trail: (id: string) => req<Trail>(`/v1/risk-events/${id}/trail`),
  pnl: () => req<PnL>("/v1/recovery/p-and-l"),
  sankey: () => req<SankeyData>("/v1/recovery/sankey"),
  escalations: () => req<Escalation[]>("/v1/escalations"),
  approve: (id: string) => req(`/v1/escalations/${id}/approve`, { method: "POST" }),
  reject: (id: string, reason: string) =>
    req(`/v1/escalations/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  outbox: () => req<OutboxMsg[]>("/v1/outbox"),
  audit: (q = "") => req<AuditRow[]>(`/v1/audit${q}`),
  scenarios: () => req<{ scenarios: string[] }>("/dev/scenarios"),
  inject: (scenario: string) =>
    req<InjectResult>("/dev/inject", { method: "POST", body: JSON.stringify({ scenario, inline: true }) }),
  recover: (scenario: string) =>
    req<RecoverResult>("/dev/recover", { method: "POST", body: JSON.stringify({ scenario }) }),
  runOutcomeTracker: () => req("/dev/run-outcome-tracker", { method: "POST" }),
  capture: (customer_id: string, amount_paise: number) =>
    req("/dev/capture", { method: "POST", body: JSON.stringify({ customer_id, amount_paise }) }),
};
