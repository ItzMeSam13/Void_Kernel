"use client";

import {
  FileSearch,
  ScanFace,
  Link2,
  History,
} from "lucide-react";
import StatusChip from "@/components/ui/StatusChip";
import Button from "@/components/ui/Button";
import type { AxisKey, Finding } from "@/lib/types";
import { AXIS_META } from "@/lib/types";

/**
 * AxisCard.tsx — One of the four axis cards on the report page (design 4.6).
 * Uses the fixed pastel mapping from design 2.2.
 */

const AXIS_ICONS: Record<string, React.ElementType> = {
  FileSearch,
  ScanFace,
  Link2,
  History,
};

interface AxisCardProps {
  axisKey: AxisKey;
  finding: Finding;
  onDetails?: () => void;
}

export default function AxisCard({
  axisKey,
  finding,
  onDetails,
}: AxisCardProps) {
  const meta = AXIS_META[axisKey];
  const Icon = AXIS_ICONS[meta.icon];

  const isAssessed = finding.status !== "not_assessed";
  const confidence = isAssessed
    ? (finding as { confidence: number }).confidence
    : null;
  const tags = isAssessed
    ? (finding as { tags: string[] }).tags
    : [];
  const modifier = isAssessed
    ? (finding as { confidenceModifier?: string }).confidenceModifier
    : undefined;

  return (
    <div
      className="rounded-[28px] transition-all duration-200 hover:-translate-y-0.5"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
        padding: 8,
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
        className="rounded-[24px] p-5"
        style={{ background: meta.pastel }}
      >
        <div className="flex items-start justify-between mb-3">
          <div>
            <p
              className="text-[15px] font-medium mb-1"
              style={{
                color: "var(--ink-400)",
                fontFamily: "var(--font-inter), sans-serif",
              }}
            >
              {meta.label}
            </p>
            <StatusChip status={finding.status} />
          </div>

          <div
            className="w-12 h-12 rounded-full flex items-center justify-center"
            style={{ background: "var(--ink-900)" }}
          >
            {Icon && (
              <Icon size={22} strokeWidth={1.5} color="white" />
            )}
          </div>
        </div>

        {/* Confidence */}
        {confidence !== null && (
          <div className="mt-3">
            <span
              className="text-[15px] font-medium"
              style={{
                color: "var(--text-on-light)",
                fontFamily:
                  "var(--font-ibm-plex-mono), monospace",
              }}
            >
              conf {confidence.toFixed(2)}
            </span>
            {modifier && (
              <span
                className="ml-3 text-[12px] font-medium px-2 py-1 rounded-full"
                style={{
                  color: "var(--status-inconclusive)",
                  background: "rgba(224,162,58,0.14)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                Confidence reduced: {modifier}
              </span>
            )}
          </div>
        )}

        {/* Not assessed reason */}
        {!isAssessed && (
          <p
            className="mt-3 text-[14px] font-medium italic"
            style={{
              color: "var(--ink-500)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            {(finding as { reason: string }).reason}
          </p>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {tags.map((tag, i) => (
              <span
                key={i}
                className="inline-block px-3 py-1.5 rounded-full text-[13px] font-medium"
                style={{
                  border: "1px solid rgba(14,14,16,0.35)",
                  color: "var(--text-on-light)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end px-4 py-3">
        <Button onClick={onDetails}>Details</Button>
      </div>
    </div>
  );
}
