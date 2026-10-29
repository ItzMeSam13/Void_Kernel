"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Bookmark,
  FileSearch,
  ScanFace,
  Link2,
  History,
  ArrowRight,
  Film,
  Image as ImageIcon,
  Mic,
  FileText,
} from "lucide-react";
import { Report, VerdictTone } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { Pill } from "@/components/ui/Pill";

interface ReportCardProps {
  report: Report;
}

export function ReportCard({ report }: ReportCardProps) {
  const [bookmarked, setBookmarked] = useState(false);

  // Determine dominant axis for card styling
  // Priority: if authenticity detected signal -> Mint; if veracity contradicted -> Peach; else Lavender / Sky
  const isAuthSignal =
    report.axes.media_authenticity.status === "ok" &&
    report.axes.media_authenticity.verdict.includes("signal");

  const isVeracityContradicted =
    report.axes.claim_veracity.status === "ok" &&
    report.axes.claim_veracity.verdict === "contradicted";

  let pastelBg = "bg-[var(--pastel-sky)]";
  let AxisIcon = History;
  let axisName = "Historical reuse";

  if (isAuthSignal) {
    pastelBg = "bg-[var(--pastel-mint)]";
    AxisIcon = ScanFace;
    axisName = "Media authenticity";
  } else if (isVeracityContradicted) {
    pastelBg = "bg-[var(--pastel-peach)]";
    AxisIcon = FileSearch;
    axisName = "Claim veracity";
  } else if (report.axes.cross_modal_consistency.status === "ok") {
    pastelBg = "bg-[var(--pastel-lavender)]";
    AxisIcon = Link2;
    axisName = "Cross-modal consistency";
  }

  // Determine primary status chip
  let tone: VerdictTone = "clear";
  let statusText = "No strong signal";
  let primaryConfidence = 0.85;

  if (isAuthSignal) {
    tone = "signal";
    statusText = "Signal detected";
    primaryConfidence =
      report.axes.media_authenticity.status === "ok"
        ? report.axes.media_authenticity.confidence
        : 0.9;
  } else if (isVeracityContradicted) {
    tone = "signal";
    statusText = "Contradicted";
    primaryConfidence =
      report.axes.claim_veracity.status === "ok"
        ? report.axes.claim_veracity.confidence
        : 0.88;
  } else if (
    report.axes.media_authenticity.status === "ok" &&
    report.axes.media_authenticity.verdict === "inconclusive"
  ) {
    tone = "inconclusive";
    statusText = "Inconclusive";
    primaryConfidence = report.axes.media_authenticity.confidence;
  }

  // Gather top signal tags
  const tags: string[] = [];
  if (report.axes.media_authenticity.status === "ok") {
    tags.push(...report.axes.media_authenticity.evidence_tags.slice(0, 2));
  }
  if (report.axes.claim_veracity.status === "ok") {
    tags.push(...report.axes.claim_veracity.evidence_tags.slice(0, 1));
  }
  if (report.axes.historical_reuse.status === "ok") {
    tags.push(...report.axes.historical_reuse.evidence_tags.slice(0, 1));
  }
  if (report.recompression_caveat) {
    tags.push("Recompression Caveat");
  }

  const MediaIcon =
    report.media_type === "video"
      ? Film
      : report.media_type === "image"
      ? ImageIcon
      : report.media_type === "audio"
      ? Mic
      : FileText;

  return (
    <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2 transition-lift select-none flex flex-col justify-between">
      {/* Inner Pastel Panel per design.md §4.5 */}
      <div className={`${pastelBg} rounded-[24px] p-5 sm:p-6 flex flex-col justify-between min-h-[300px]`}>
        {/* Top Row: Date Pill & Bookmark Button */}
        <div className="flex items-center justify-between">
          <div className="bg-white px-3.5 py-1.5 rounded-full text-[13px] font-medium text-[var(--text-on-light)] shadow-xs flex items-center gap-1.5">
            <MediaIcon className="w-3.5 h-3.5 text-[var(--ink-500)]" />
            <span>{report.created_at}</span>
          </div>

          <button
            onClick={() => setBookmarked(!bookmarked)}
            className="w-11 h-11 rounded-full bg-white flex items-center justify-center text-[var(--ink-900)] shadow-xs hover:bg-[var(--ink-100)] transition-transform active:scale-90"
            aria-label="Bookmark check"
          >
            <Bookmark
              className={`w-4 h-4 ${
                bookmarked ? "fill-[var(--ink-900)] text-[var(--ink-900)]" : "text-[var(--ink-900)]"
              }`}
            />
          </button>
        </div>

        {/* Center: Axis Label, Title & Icon Badge */}
        <div className="my-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[14px] font-medium text-[var(--text-on-light)]/80">
              {axisName} · {report.media_type.toUpperCase()}
            </span>

            {/* 48px round icon badge in black per design.md §4.5 */}
            <div className="w-11 h-11 rounded-full bg-[var(--ink-900)] flex items-center justify-center text-white shrink-0 shadow-sm">
              <AxisIcon className="w-5 h-5" strokeWidth={1.75} />
            </div>
          </div>

          <h3 className="font-display font-semibold text-[22px] sm:text-[24px] leading-[1.25] text-[var(--text-on-light)] line-clamp-2">
            {report.claim_text}
          </h3>
        </div>

        {/* Tag Pills Row */}
        <div className="flex flex-wrap gap-2 pt-2">
          {tags.slice(0, 4).map((tag, idx) => (
            <Pill key={idx} variant="outline">
              {tag}
            </Pill>
          ))}
        </div>
      </div>

      {/* Footer Row (outside pastel panel, inside white shell) per design.md §4.5 */}
      <div className="flex items-center justify-between px-3.5 py-3 mt-1">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2.5">
            <StatusChip tone={tone} label={statusText} size="sm" />
            <span className="text-[13px] font-mono font-medium text-[var(--ink-500)]">
              conf {primaryConfidence.toFixed(2)}
            </span>
          </div>
          <span className="text-[12px] text-[var(--ink-400)] font-mono">
            ID: {report.job_id} · {report.language}
          </span>
        </div>

        <Link href={`/results/${report.job_id}`}>
          <button className="h-[48px] px-6 rounded-full bg-[var(--ink-900)] hover:bg-[var(--ink-800)] text-white text-[14px] font-semibold flex items-center gap-1.5 transition-transform active:scale-95 cursor-pointer">
            <span>Details</span>
            <ArrowRight className="w-4 h-4 ml-0.5" />
          </button>
        </Link>
      </div>
    </div>
  );
}

