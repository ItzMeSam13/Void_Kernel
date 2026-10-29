"use client";

import React from "react";
import { ShieldCheck, Info } from "lucide-react";

interface ExplanationPanelProps {
  explanation: string;
  onSelectCitation?: (index: number) => void;
  activeCitation?: number | null;
}

export function ExplanationPanel({
  explanation,
  onSelectCitation,
  activeCitation,
}: ExplanationPanelProps) {
  // Parse sentences and [1], [2], [3] citations
  const parts = explanation.split(/(\[\d+\])/g);

  return (
    <div className="w-full rounded-[28px] bg-[var(--pastel-grey)] p-6 sm:p-8 select-none border border-[var(--ink-200)]/60">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-display font-bold text-[22px] sm:text-[24px] text-[var(--text-on-light)] tracking-tight">
          Evidence-Grounded Explanation
        </h4>
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/80 border border-[var(--ink-200)] text-[12px] font-medium text-[var(--ink-500)]">
          <ShieldCheck className="w-3.5 h-3.5 text-[var(--status-clear)]" />
          <span>Wording checked against evidence</span>
        </div>
      </div>

      {/* Main explanation body with interactive superscript citations */}
      <p className="text-[16px] sm:text-[17px] leading-[1.65] text-[var(--text-on-light)] font-normal">
        {parts.map((part, idx) => {
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const citeNum = parseInt(match[1], 10);
            const isHighlight = activeCitation === citeNum - 1;
            return (
              <button
                key={idx}
                onClick={() => onSelectCitation?.(citeNum - 1)}
                className={`inline-flex items-center justify-center w-5 h-5 -mt-1 mx-0.5 rounded-full text-[11px] font-bold transition-all cursor-pointer ${
                  isHighlight
                    ? "bg-[var(--ink-900)] text-white scale-110 shadow-xs"
                    : "bg-white text-[var(--ink-700)] hover:bg-[var(--accent-sky)] hover:text-[var(--ink-900)] border border-[var(--ink-200)]"
                }`}
                title={`Jump to evidence [${citeNum}]`}
              >
                {citeNum}
              </button>
            );
          }
          return <span key={idx}>{part}</span>;
        })}
      </p>

      {/* Persistent footer rule per design.md §8: "Results are evidence signals, not proof." */}
      <div className="mt-6 pt-4 border-t border-[var(--ink-200)]/70 flex flex-wrap items-center justify-between gap-3 text-[13px] text-[var(--ink-500)]">
        <div className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-[var(--ink-400)] shrink-0" />
          <span>Results are evidence signals, not definitive proof of manipulation.</span>
        </div>
        <span className="font-mono text-[12px] text-[var(--ink-400)]">
          Gemini 1.5 Flash grounded prompt (Node 11)
        </span>
      </div>
    </div>
  );
}

