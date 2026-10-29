"use client";

import React from "react";
import { ExternalLink, AlertTriangle, ShieldCheck, HelpCircle } from "lucide-react";
import { EvidenceItem } from "@/lib/types";

interface EvidenceRowProps {
  item: EvidenceItem;
  citationIndex?: number;
  isHighlighted?: boolean;
}

export function EvidenceRow({
  item,
  citationIndex,
  isHighlighted,
}: EvidenceRowProps) {
  let stanceBg = "bg-[#2FAE8F]/15 text-[#1C826A] border-[#2FAE8F]/30";
  let StanceIcon = ShieldCheck;
  let stanceLabel = "Supports claim";

  if (item.stance === "contradicts") {
    stanceBg = "bg-[#E8667A]/15 text-[#C7384E] border-[#E8667A]/30";
    StanceIcon = AlertTriangle;
    stanceLabel = "Contradicts claim";
  } else if (item.stance === "neutral" || item.stance === "unverifiable") {
    stanceBg = "bg-[#E0A23A]/15 text-[#B37817] border-[#E0A23A]/30";
    StanceIcon = HelpCircle;
    stanceLabel = "Neutral / Context";
  }

  return (
    <div
      className={`rounded-[20px] p-5 bg-white border transition-all duration-200 ${
        isHighlighted
          ? "border-[var(--ink-900)] ring-2 ring-[var(--accent-sky-600)] shadow-md"
          : "border-[var(--ink-200)] hover:border-[var(--ink-400)]"
      }`}
    >
      {/* Echo-Chamber Warning Banner per design.md §4.6 & architecture.md Module 6 */}
      {item.echo_chamber_flag && (
        <div className="mb-3.5 px-3.5 py-2 rounded-[12px] bg-[var(--pastel-peach)] border border-[var(--status-signal)]/20 flex items-center justify-between text-[12px]">
          <div className="flex items-center gap-2 text-[#9B2A3B] font-medium">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>Echo-Chamber Signal: domain repeated or wire-story syndication detected</span>
          </div>
          <span className="font-mono text-[11px] text-[#9B2A3B]">
            weight ×0.75
          </span>
        </div>
      )}

      {/* Row Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2.5">
          {citationIndex !== undefined && (
            <span className="w-6 h-6 rounded-full bg-[var(--ink-900)] text-white text-[12px] font-bold flex items-center justify-center shrink-0">
              {citationIndex + 1}
            </span>
          )}
          <span className="font-semibold text-[15px] text-[var(--text-on-light)]">
            {item.source_name}
          </span>
          <span className="text-[13px] font-mono text-[var(--ink-400)]">
            ({item.domain})
          </span>
        </div>

        {/* Stance chip */}
        <div
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[12px] font-semibold border ${stanceBg}`}
        >
          <StanceIcon className="w-3.5 h-3.5" />
          <span>{stanceLabel}</span>
        </div>
      </div>

      {/* Snippet */}
      <p className="text-[14px] leading-relaxed text-[var(--ink-500)] mb-3">
        &ldquo;{item.snippet}&rdquo;
      </p>

      {/* Meta + Link */}
      <div className="flex items-center justify-between pt-2 border-t border-[var(--ink-100)] text-[12px] text-[var(--ink-400)]">
        <span>Published: {item.published_at || "Recent dispatch"}</span>
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[var(--accent-sky-600)] hover:text-[var(--ink-900)] font-medium transition-colors"
        >
          <span>View original source</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  );
}

