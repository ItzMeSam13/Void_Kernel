"use client";

import Link from "next/link";
import {
  Bookmark,
  FileSearch,
  ScanFace,
  Link2,
  History,
} from "lucide-react";
import StatusChip from "@/components/ui/StatusChip";
import Button from "@/components/ui/Button";
import type { Report, AxisKey, Finding, VerdictState } from "@/lib/types";
import { AXIS_META } from "@/lib/types";

/**
 * ReportCard.tsx — The main repeated card unit (design 4.5).
 * White outer shell → pastel inner panel → footer row.
 */

const AXIS_ICONS: Record<string, React.ElementType> = {
  FileSearch,
  ScanFace,
  Link2,
  History,
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${d.getDate()} ${months[d.getMonth()]}, ${d.getFullYear()}`;
}

/** Pick the most "interesting" axis to feature on the card */
function primaryAxis(report: Report): {
  axisKey: AxisKey;
  finding: Finding;
} {
  const priority: VerdictState[] = [
    "signal_detected",
    "inconclusive",
    "checking",
    "in_queue",
    "no_strong_signal",
    "not_assessed",
  ];
  let best: { axisKey: AxisKey; finding: Finding } | null = null;
  let bestIdx = priority.length;

  for (const [key, finding] of Object.entries(report.axes)) {
    const idx = priority.indexOf(finding.status);
    if (idx < bestIdx) {
      bestIdx = idx;
      best = { axisKey: key as AxisKey, finding };
    }
  }
  return best ?? {
    axisKey: "claim_veracity",
    finding: report.axes.claim_veracity,
  };
}

interface ReportCardProps {
  report: Report;
  index?: number;
}

export default function ReportCard({ report, index = 0 }: ReportCardProps) {
  const { axisKey, finding } = primaryAxis(report);
  const meta = AXIS_META[axisKey];
  const Icon = AXIS_ICONS[meta.icon];

  const confidence =
    finding.status !== "not_assessed"
      ? (finding as { confidence: number }).confidence
      : null;

  const tags =
    finding.status !== "not_assessed"
      ? (finding as { tags: string[] }).tags
      : [];

  const mediaLabel =
    report.mediaType.charAt(0).toUpperCase() + report.mediaType.slice(1);

  return (
    <div
      className="card-enter rounded-[28px] transition-all duration-200 hover:-translate-y-0.5"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
        padding: 8,
        animationDelay: `${index * 30}ms`,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow =
          "0 8px 24px rgba(20,20,40,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      {/* Inner pastel panel */}
      <div
        className="rounded-[24px] p-5 relative"
        style={{ background: meta.pastel }}
      >
        {/* Top row: date chip + bookmark */}
        <div className="flex items-start justify-between mb-4">
          <span
            className="inline-block px-4 py-2.5 rounded-full text-[14px] font-medium"
            style={{
              background: "white",
              color: "var(--text-on-light)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            {formatDate(report.createdAt)}
          </span>

          <button
            className="w-11 h-11 rounded-full flex items-center justify-center transition-colors duration-150"
            style={{ background: "white" }}
            aria-label={
              report.bookmarked ? "Remove bookmark" : "Save for review"
            }
          >
            <Bookmark
              size={18}
              strokeWidth={1.5}
              fill={report.bookmarked ? "var(--ink-900)" : "none"}
              color="var(--ink-900)"
            />
          </button>
        </div>

        {/* Small label */}
        <p
          className="text-[15px] font-medium mb-1"
          style={{
            color: "rgba(17,17,20,0.8)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          {meta.label} · {mediaLabel}
        </p>

        {/* Title and icon */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <h3
            className="text-[28px] leading-[32px] font-semibold"
            style={{
              color: "var(--text-on-light)",
              fontFamily: "var(--font-manrope), sans-serif",
              textWrap: "balance" as unknown as string,
              maxWidth: "calc(100% - 60px)",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {report.claimText}
          </h3>

          {/* Round icon badge */}
          <div
            className="w-12 h-12 rounded-full shrink-0 flex items-center justify-center"
            style={{ background: "var(--ink-900)" }}
          >
            {Icon && (
              <Icon size={22} strokeWidth={1.5} color="white" />
            )}
          </div>
        </div>

        {/* Tag pills */}
        <div className="flex flex-wrap gap-2">
          {tags.slice(0, 4).map((tag, i) => (
            <span
              key={i}
              className="inline-block px-3.5 py-2 rounded-full text-[13px] font-medium"
              style={{
                border: "1px solid rgba(14,14,16,0.35)",
                color: "var(--text-on-light)",
                fontFamily: "var(--font-inter), sans-serif",
              }}
            >
              {tag}
            </span>
          ))}
          {finding.status === "not_assessed" && (
            <span
              className="inline-block px-3.5 py-2 rounded-full text-[13px] font-medium italic"
              style={{
                border: "1px solid rgba(14,14,16,0.25)",
                color: "var(--ink-400)",
              }}
            >
              {(finding as { reason: string }).reason}
            </span>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <StatusChip status={finding.status} />
            {confidence !== null && (
              <span
                className="text-[13px] font-medium"
                style={{
                  color: "var(--ink-500)",
                  fontFamily:
                    "var(--font-ibm-plex-mono), monospace",
                }}
              >
                conf {confidence.toFixed(2)}
              </span>
            )}
          </div>
          {(report.source || report.language) && (
            <span
              className="text-[12px] font-medium"
              style={{
                color: "var(--ink-400)",
                fontFamily: "var(--font-inter), sans-serif",
              }}
            >
              {[report.source, report.language]
                .filter(Boolean)
                .join(" · ")}
            </span>
          )}
        </div>

        <Link href={`/results/${report.id}`}>
          <Button>Details</Button>
        </Link>
      </div>
    </div>
  );
}
