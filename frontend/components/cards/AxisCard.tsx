"use client";

import React from "react";
import {
  FileSearch,
  ScanFace,
  Link2,
  History,
  ArrowRight,
  Info,
} from "lucide-react";
import {
  ClaimVeracityFinding,
  MediaAuthenticityFinding,
  CrossModalConsistencyFinding,
  HistoricalReuseFinding,
  VerdictTone,
} from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { Pill } from "@/components/ui/Pill";

type AxisType =
  | "claim_veracity"
  | "media_authenticity"
  | "cross_modal_consistency"
  | "historical_reuse";

interface AxisCardProps {
  axisType: AxisType;
  finding:
    | ClaimVeracityFinding
    | MediaAuthenticityFinding
    | CrossModalConsistencyFinding
    | HistoricalReuseFinding;
  onOpenDrawer?: () => void;
}

export function AxisCard({
  axisType,
  finding,
  onOpenDrawer,
}: AxisCardProps) {
  // Axis identity configuration per design.md §2.2
  let title = "Claim veracity";
  let pastelBg = "bg-[var(--pastel-peach)]";
  let Icon = FileSearch;

  if (axisType === "media_authenticity") {
    title = "Media authenticity";
    pastelBg = "bg-[var(--pastel-mint)]";
    Icon = ScanFace;
  } else if (axisType === "cross_modal_consistency") {
    title = "Cross-modal consistency";
    pastelBg = "bg-[var(--pastel-lavender)]";
    Icon = Link2;
  } else if (axisType === "historical_reuse") {
    title = "Historical reuse";
    pastelBg = "bg-[var(--pastel-sky)]";
    Icon = History;
  }

  // Handle not_assessed state per design.md §1 & §4.7
  if (finding.status === "not_assessed") {
    return (
      <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2 select-none flex flex-col justify-between">
        <div className="bg-[var(--ink-100)] rounded-[24px] p-6 flex flex-col justify-between min-h-[260px]">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[14px] font-medium text-[var(--ink-400)]">
                Axis 0{axisType === "claim_veracity" ? 1 : axisType === "media_authenticity" ? 2 : axisType === "cross_modal_consistency" ? 3 : 4}
              </span>
              <div className="w-10 h-10 rounded-full bg-[var(--ink-200)] flex items-center justify-center text-[var(--ink-500)]">
                <Icon className="w-5 h-5" strokeWidth={1.75} />
              </div>
            </div>
            <h3 className="font-display font-semibold text-[26px] text-[var(--ink-500)]">
              {title}
            </h3>
            <p className="mt-3 text-[14px] text-[var(--ink-500)] leading-relaxed flex items-start gap-2">
              <Info className="w-4 h-4 text-[var(--ink-400)] shrink-0 mt-0.5" />
              <span>{finding.reason}</span>
            </p>
          </div>

          <div className="pt-4">
            <StatusChip tone="na" label="Not assessed" />
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-[13px] text-[var(--ink-400)]">
            No inference performed
          </span>
          <button
            onClick={onOpenDrawer}
            className="h-[46px] px-5 rounded-full border border-[var(--ink-200)] hover:bg-[var(--ink-100)] text-[var(--ink-500)] text-[13px] font-medium"
          >
            Details
          </button>
        </div>
      </div>
    );
  }

  // Mapping findings to status chip tone and label
  let tone: VerdictTone = "clear";
  let label = "No strong signal";

  if (axisType === "claim_veracity") {
    const v = finding.verdict;
    if (v === "contradicted") {
      tone = "signal";
      label = "Contradicted";
    } else if (v === "supported") {
      tone = "clear";
      label = "Supported";
    } else {
      tone = "inconclusive";
      label = "Uncertain";
    }
  } else if (axisType === "media_authenticity") {
    const v = finding.verdict;
    if (v.includes("signal") || v.includes("detected") || v.includes("suspicious")) {
      tone = "signal";
      label = "Signal detected";
    } else if (v === "inconclusive") {
      tone = "inconclusive";
      label = "Inconclusive";
    } else {
      tone = "clear";
      label = "No strong signal";
    }
  } else if (axisType === "cross_modal_consistency") {
    const v = finding.verdict;
    if (v === "entity_mismatch" || v === "text_image_drift") {
      tone = "signal";
      label = "Mismatch detected";
    } else if (v === "inconclusive") {
      tone = "inconclusive";
      label = "Inconclusive";
    } else {
      tone = "clear";
      label = "Consistent";
    }
  } else if (axisType === "historical_reuse") {
    const v = finding.verdict;
    if (v === "exact_match" || v === "near_match") {
      tone = "signal";
      label = "Prior match found";
    } else {
      tone = "clear";
      label = "Novel media";
    }
  }

  return (
    <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2 transition-lift select-none flex flex-col justify-between">
      {/* Inner Pastel Panel with Fixed Color per design.md §2.2 */}
      <div className={`${pastelBg} rounded-[24px] p-6 flex flex-col justify-between min-h-[260px]`}>
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[13px] font-medium tracking-wide text-[var(--text-on-light)]/75 uppercase">
              Axis {axisType === "claim_veracity" ? "01" : axisType === "media_authenticity" ? "02" : axisType === "cross_modal_consistency" ? "03" : "04"}
            </span>
            <div className="w-11 h-11 rounded-full bg-[var(--ink-900)] flex items-center justify-center text-white shadow-xs">
              <Icon className="w-5 h-5" strokeWidth={1.75} />
            </div>
          </div>

          <h3 className="font-display font-bold text-[26px] sm:text-[28px] text-[var(--text-on-light)] leading-tight">
            {title}
          </h3>
        </div>

        {/* Evidence Tags */}
        <div className="flex flex-wrap gap-2 pt-4">
          {finding.evidence_tags.slice(0, 3).map((tag, idx) => (
            <Pill key={idx} variant="outline">
              {tag}
            </Pill>
          ))}
        </div>
      </div>

      {/* Footer Row */}
      <div className="flex items-center justify-between px-4 py-3 mt-1">
        <div className="flex items-center gap-3">
          <StatusChip tone={tone} label={label} size="sm" />
          <span className="text-[13px] font-mono font-medium text-[var(--ink-500)]">
            conf {finding.confidence.toFixed(2)}
          </span>
        </div>

        <button
          onClick={onOpenDrawer}
          className="h-[46px] px-5 rounded-full bg-[var(--ink-900)] hover:bg-[var(--ink-800)] text-white text-[13px] font-semibold flex items-center gap-1.5 transition-transform active:scale-95 cursor-pointer"
        >
          <span>Evidence</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

