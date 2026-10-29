"use client";

import React from "react";
import { ArrowUpRight } from "lucide-react";

interface PromoCardProps {
  onLearnMore?: () => void;
}

export function PromoCard({ onLearnMore }: PromoCardProps) {
  return (
    <div className="relative w-full rounded-[28px] bg-[var(--ink-900)] p-8 text-white overflow-hidden shadow-sm flex flex-col justify-between min-h-[340px] select-none">
      {/* Decorative thin arc line art (18% opacity) per design.md §4.3 */}
      <svg
        className="absolute top-0 right-0 w-full h-full pointer-events-none opacity-20"
        viewBox="0 0 320 340"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="280" cy="50" r="140" stroke="white" strokeWidth="1" />
        <circle cx="280" cy="50" r="220" stroke="white" strokeWidth="1" strokeDasharray="3 4" />
        <path d="M 0 280 C 120 220, 200 300, 320 200" stroke="white" strokeWidth="1" />
      </svg>

      {/* Heading */}
      <div className="relative z-10">
        <span className="text-[12px] font-semibold tracking-wider text-[var(--accent-sky)] uppercase mb-3 block">
          Truth & Provenance
        </span>
        <h2 className="font-display font-extrabold text-[32px] sm:text-[34px] leading-[1.15] text-white max-w-[240px]">
          Verify before you forward.
        </h2>
        <p className="mt-3 text-[14px] text-[var(--text-on-dark-muted)] leading-relaxed">
          Four independent verification axes: media authenticity, claim veracity, cross-modal consistency, and historical reuse.
        </p>
      </div>

      {/* CTA Button per design.md §4.3 */}
      <div className="relative z-10 mt-6">
        <button
          onClick={onLearnMore}
          className="w-full h-14 rounded-full bg-[var(--accent-sky)] hover:bg-[var(--accent-sky-600)] text-[var(--ink-900)] font-semibold text-[15px] flex items-center justify-center gap-2 transition-transform active:scale-[0.98] cursor-pointer"
        >
          <span>Learn how it works</span>
          <ArrowUpRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

