/**
 * Nith (Void Kernel) Frontend Types
 * Matches architecture.md and design.md specs.
 *
 * Guiding principle:
 * Each axis finding is a tagged union with status: "ok" | "not_assessed",
 * ensuring the UI can never fabricate or display a numerical score
 * for an unassessed component.
 */

export type Modality = "image" | "video" | "audio" | "text";

export type VerdictTone = "signal" | "clear" | "inconclusive" | "na" | "running" | "queued";

// ── Axis Status & Verdicts ──────────────────────────────────────────────────

export type ClaimVeracityVerdict =
  | "supported"
  | "contradicted"
  | "uncertain"
  | "unverifiable"
  | "not_assessed";

export type MediaAuthenticityVerdict =
  | "synthetic_audio_signal_detected"
  | "suspicious_frames"
  | "deepfake_detected"
  | "no_strong_signal_detected"
  | "inconclusive"
  | "not_assessed";

export type CrossModalConsistencyVerdict =
  | "consistent"
  | "entity_mismatch"
  | "text_image_drift"
  | "inconclusive"
  | "not_assessed";

export type HistoricalReuseVerdict =
  | "exact_match"
  | "near_match"
  | "novel"
  | "unverified"
  | "not_assessed";

// ── Tagged Unions for Axis Findings ─────────────────────────────────────────

export type ClaimVeracityFinding =
  | {
      status: "ok";
      verdict: ClaimVeracityVerdict;
      confidence: number;
      evidence_summary: string;
      evidence_tags: string[];
      claims_checked_count: number;
      echo_chamber_detected?: boolean;
    }
  | {
      status: "not_assessed";
      verdict: "not_assessed";
      reason: string;
    };

export type MediaAuthenticityFinding =
  | {
      status: "ok";
      verdict: MediaAuthenticityVerdict;
      confidence: number;
      stage_reached: 1 | 2 | 3;
      concrete_evidence: string[];
      evidence_tags: string[];
      spectral_artifact_score?: number | null;
      signal_integrity_score?: number | null;
      confounded_by_recompression: boolean;
      saliency_heatmap_path?: string | null;
    }
  | {
      status: "not_assessed";
      verdict: "not_assessed";
      reason: string;
    };

export type CrossModalConsistencyFinding =
  | {
      status: "ok";
      verdict: CrossModalConsistencyVerdict;
      confidence: number;
      mismatch_details?: string | null;
      evidence_tags: string[];
    }
  | {
      status: "not_assessed";
      verdict: "not_assessed";
      reason: string;
    };

export type HistoricalReuseFinding =
  | {
      status: "ok";
      verdict: HistoricalReuseVerdict;
      confidence: number;
      source_url?: string | null;
      source_published_at?: string | null;
      source_location?: string | null;
      hamming_distance?: number | null;
      evidence_tags: string[];
    }
  | {
      status: "not_assessed";
      verdict: "not_assessed";
      reason: string;
    };

// ── Evidence Item ───────────────────────────────────────────────────────────

export interface EvidenceItem {
  id: string;
  domain: string;
  source_name: string;
  url: string;
  published_at?: string;
  stance: "supports" | "contradicts" | "neutral" | "unverifiable";
  snippet: string;
  echo_chamber_flag?: boolean;
  confidence_multiplier?: number;
}

// ── Flagged Video/Audio Segments ───────────────────────────────────────────

export interface FlaggedSegment {
  start_sec: number;
  end_sec: number;
  label: string;
  score: number;
  description: string;
}

// ── Comprehensive Report ────────────────────────────────────────────────────

export interface Report {
  job_id: string;
  sha256: string;
  created_at: string;
  media_type: Modality;
  filename: string;
  media_preview_url?: string | null;
  claim_text: string;
  language: string;
  explanation: string;
  explanation_citation_indexes?: number[]; // positions corresponding to evidence array
  axes: {
    claim_veracity: ClaimVeracityFinding;
    media_authenticity: MediaAuthenticityFinding;
    cross_modal_consistency: CrossModalConsistencyFinding;
    historical_reuse: HistoricalReuseFinding;
  };
  evidence: EvidenceItem[];
  flagged_segments: FlaggedSegment[];
  recompression_caveat: boolean;
  status: "queued" | "processing" | "done" | "failed";
  error_message?: string | null;
}

// ── Module 8 Evaluation Metrics ─────────────────────────────────────────────

export interface EvalMetric {
  module: string;
  module_name: string;
  owner: string;
  accuracy: number;
  f1_score: number;
  false_positive_rate: number;
  fpr_ci_95: string; // e.g. "4.1% – 11.2%"
  latency_ms_p95: number;
  sample_count: number;
  last_evaluated: string;
  notes: string;
  slices: Array<{
    category: string;
    value: string;
    sample_size: number;
    accuracy: number;
    fpr: number;
  }>;
}

