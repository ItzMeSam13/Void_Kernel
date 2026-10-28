"use client";

import { CheckCircle2 } from "lucide-react";

/**
 * ExplanationPanel.tsx — Explanation section on the report page (design 4.6).
 * Pastel-grey background with explanation text and bias regulator indicator.
 */

interface ExplanationPanelProps {
  text: string;
  biasRegulatorRan?: boolean;
}

export default function ExplanationPanel({
  text,
  biasRegulatorRan,
}: ExplanationPanelProps) {
  return (
    <div
      className="rounded-[24px] p-6"
      style={{
        background: "var(--pastel-grey)",
      }}
    >
      <h3
        className="text-[15px] font-medium mb-3"
        style={{
          color: "var(--ink-400)",
          fontFamily: "var(--font-inter), sans-serif",
        }}
      >
        Explanation
      </h3>

      <p
        className="text-[15px] leading-[22px]"
        style={{
          color: "var(--text-on-light)",
          fontFamily: "var(--font-inter), sans-serif",
        }}
      >
        {text}
      </p>

      {biasRegulatorRan && (
        <div
          className="flex items-center gap-2 mt-4 pt-4"
          style={{ borderTop: "1px solid var(--ink-200)" }}
        >
          <CheckCircle2
            size={14}
            strokeWidth={1.5}
            color="var(--status-clear)"
          />
          <span
            className="text-[12px] font-medium"
            style={{
              color: "var(--ink-400)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            Wording checked against evidence
          </span>
        </div>
      )}
    </div>
  );
}
