/* ──────────────────────────────────────────────────────────
   lib/types.ts – Mirrors backend Pydantic contracts
   Four axes, tagged-union statuses, report & evidence types.
   ────────────────────────────────────────────────────────── */

// ─── Status ──────────────────────────────────────────────

export type VerdictState =
  | "signal_detected"
  | "no_strong_signal"
  | "inconclusive"
  | "not_assessed"
  | "checking"
  | "in_queue";

export type EvidenceStance = "supports" | "contradicts" | "neutral";

// ─── Axis types ──────────────────────────────────────────

export type AxisKey =
  | "claim_veracity"
  | "media_authenticity"
  | "cross_modal_consistency"
  | "historical_reuse";

export const AXIS_META: Record<
  AxisKey,
  { label: string; icon: string; pastel: string }
> = {
  claim_veracity: {
    label: "Claim veracity",
    icon: "FileSearch",
    pastel: "var(--pastel-peach)",
  },
  media_authenticity: {
    label: "Media authenticity",
    icon: "ScanFace",
    pastel: "var(--pastel-mint)",
  },
  cross_modal_consistency: {
    label: "Cross-modal consistency",
    icon: "Link2",
    pastel: "var(--pastel-lavender)",
  },
  historical_reuse: {
    label: "Historical reuse",
    icon: "History",
    pastel: "var(--pastel-sky)",
  },
};

// ─── Finding (tagged union) ──────────────────────────────

export interface AssessedFinding {
  status: Exclude<VerdictState, "not_assessed">;
  confidence: number; // 0 – 1
  tags: string[]; // e.g. ["Smaug 0.42", "ManTraNet clear"]
  confidenceModifier?: string; // e.g. "recompression"
}

export interface NotAssessedFinding {
  status: "not_assessed";
  reason: string; // e.g. "Audio too short"
}

export type Finding = AssessedFinding | NotAssessedFinding;

// ─── Evidence ────────────────────────────────────────────

export interface EvidenceItem {
  id: string;
  sourceDomain: string;
  date: string;
  stance: EvidenceStance;
  snippet: string;
  url: string;
  isEchoChamber?: boolean;
}

// ─── Report ──────────────────────────────────────────────

export interface Report {
  id: string;
  claimText: string;
  mediaType: "image" | "video" | "audio" | "text";
  mediaUrl?: string;
  language: string;
  source?: string; // e.g. "Telegram"
  createdAt: string; // ISO date
  bookmarked: boolean;
  axes: Record<AxisKey, Finding>;
  explanation?: string;
  evidenceItems: EvidenceItem[];
  biasRegulatorRan?: boolean;
  heatmapUrl?: string;
  videoTimeline?: { timestamp: number; label: string }[];
}

// ─── Eval / Analytics ────────────────────────────────────

export interface ModuleMetrics {
  module: string;
  precision: number;
  recall: number;
  fpr: number;
  latencyP50: number;
  latencyP95: number;
  n: number;
  ci95Low: number;
  ci95High: number;
}

export interface SliceRow {
  dimension: string;
  value: string;
  precision: number;
  recall: number;
  fpr: number;
  n: number;
}

export interface EvalData {
  metrics: ModuleMetrics[];
  slices: SliceRow[];
  riskCoverage: { risk: number; coverage: number }[];
  isDemoData: boolean;
}

// ─── API responses ───────────────────────────────────────

export interface JobSubmitResponse {
  jobId: string;
}

export interface ReportsListResponse {
  reports: Report[];
  total: number;
}
