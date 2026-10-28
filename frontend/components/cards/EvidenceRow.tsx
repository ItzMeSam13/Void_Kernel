"use client";

import type { EvidenceItem } from "@/lib/types";
import { ExternalLink } from "lucide-react";
import StatusChip from "@/components/ui/StatusChip";

/**
 * EvidenceRow.tsx — Evidence list item (design 4.6).
 * Source domain, date, stance chip, snippet, external link.
 */

const stanceToVerdict = {
  supports: "no_strong_signal" as const,
  contradicts: "signal_detected" as const,
  neutral: "inconclusive" as const,
};

interface EvidenceRowProps {
  item: EvidenceItem;
  highlighted?: boolean;
}

export default function EvidenceRow({
  item,
  highlighted = false,
}: EvidenceRowProps) {
  return (
    <div
      className="rounded-[20px] p-5 transition-colors duration-150"
      style={{
        background: highlighted ? "var(--ink-100)" : "var(--card)",
        border: "1px solid var(--ink-200)",
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-3 flex-wrap">
          <span
            className="text-[15px] font-semibold"
            style={{
              color: "var(--text-on-light)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            {item.sourceDomain}
          </span>
          <span
            className="text-[12px] font-medium"
            style={{
              color: "var(--ink-400)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            {item.date}
          </span>
          <StatusChip status={stanceToVerdict[item.stance]} />
        </div>

        {item.url !== "#" && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center transition-colors duration-150"
            style={{ border: "1px solid var(--ink-200)" }}
            aria-label={`Open source: ${item.sourceDomain}`}
          >
            <ExternalLink
              size={14}
              strokeWidth={1.5}
              color="var(--ink-500)"
            />
          </a>
        )}
      </div>

      <p
        className="text-[15px] leading-[22px]"
        style={{
          color: "var(--text-on-light)",
          fontFamily: "var(--font-inter), sans-serif",
        }}
      >
        {item.snippet}
      </p>

      {item.isEchoChamber && (
        <div
          className="mt-3 px-4 py-3 rounded-xl text-[13px] font-medium"
          style={{
            background: "var(--pastel-peach)",
            color: "var(--text-on-light)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          ⚠ Echo-chamber warning: This source may amplify rather
          than independently verify the claim.
        </div>
      )}
    </div>
  );
}
