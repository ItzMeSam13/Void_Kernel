"use client";

import React, { useState } from "react";
import { Search, Film, Globe, SlidersHorizontal } from "lucide-react";

interface ClaimBarProps {
  claimQuery: string;
  onClaimQueryChange: (q: string) => void;
  mediaType: string;
  onMediaTypeChange: (m: string) => void;
  confidenceRange: [number, number];
  onConfidenceRangeChange: (range: [number, number]) => void;
  onSubmitSearch?: () => void;
}

export function ClaimBar({
  claimQuery,
  onClaimQueryChange,
  mediaType,
  onMediaTypeChange,
  confidenceRange,
  onConfidenceRangeChange,
  onSubmitSearch,
}: ClaimBarProps) {
  const [language, setLanguage] = useState("All languages");
  const [sortView, setSortView] = useState("Latest");

  return (
    <div className="w-full bg-[var(--ink-900)] px-6 md:px-14 py-4 md:py-6 border-b border-[var(--ink-700)] select-none">
      <div className="flex flex-col xl:flex-row items-stretch xl:items-center gap-4 xl:gap-6 justify-between">
        {/* Left 4 Controls Group */}
        <div className="flex flex-wrap lg:flex-nowrap items-center gap-4 xl:gap-5 flex-1">
          {/* 1. Claim Search Input */}
          <div className="flex items-center gap-3.5 flex-1 min-w-[240px]">
            <div className="w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white shrink-0">
              <Search className="w-5 h-5 text-[var(--accent-sky)]" />
            </div>
            <div className="flex-1 flex flex-col">
              <span className="text-[12px] font-medium text-[var(--text-on-dark-muted)]">
                Claim / Keyword
              </span>
              <input
                type="text"
                value={claimQuery}
                onChange={(e) => onClaimQueryChange(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && onSubmitSearch?.()}
                placeholder="Paste a claim or caption…"
                className="bg-transparent text-white text-[15px] font-medium placeholder-[var(--ink-400)] outline-none w-full"
              />
            </div>
          </div>

          <div className="hidden lg:block w-[1px] h-10 bg-[var(--ink-700)]" />

          {/* 2. Media Type Selector */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white shrink-0">
              <Film className="w-5 h-5 text-white/80" />
            </div>
            <div className="flex flex-col">
              <span className="text-[12px] font-medium text-[var(--text-on-dark-muted)]">
                Media type
              </span>
              <select
                value={mediaType}
                onChange={(e) => onMediaTypeChange(e.target.value)}
                className="bg-transparent text-white text-[14px] font-medium outline-none cursor-pointer pr-4 appearance-none"
                style={{
                  backgroundImage:
                    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E\")",
                  backgroundRepeat: "no-repeat",
                  backgroundPosition: "right center",
                }}
              >
                <option value="all" className="bg-[var(--ink-900)] text-white">
                  All media
                </option>
                <option value="video" className="bg-[var(--ink-900)] text-white">
                  Video
                </option>
                <option value="image" className="bg-[var(--ink-900)] text-white">
                  Image
                </option>
                <option value="audio" className="bg-[var(--ink-900)] text-white">
                  Audio
                </option>
                <option value="text" className="bg-[var(--ink-900)] text-white">
                  Text only
                </option>
              </select>
            </div>
          </div>

          <div className="hidden lg:block w-[1px] h-10 bg-[var(--ink-700)]" />

          {/* 3. Language Selector */}
          <div className="hidden sm:flex items-center gap-3 shrink-0">
            <div className="w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white shrink-0">
              <Globe className="w-5 h-5 text-white/80" />
            </div>
            <div className="flex flex-col">
              <span className="text-[12px] font-medium text-[var(--text-on-dark-muted)]">
                Language
              </span>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="bg-transparent text-white text-[14px] font-medium outline-none cursor-pointer pr-4 appearance-none"
                style={{
                  backgroundImage:
                    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E\")",
                  backgroundRepeat: "no-repeat",
                  backgroundPosition: "right center",
                }}
              >
                <option value="All languages" className="bg-[var(--ink-900)] text-white">
                  All languages
                </option>
                <option value="English" className="bg-[var(--ink-900)] text-white">
                  English
                </option>
                <option value="Hindi" className="bg-[var(--ink-900)] text-white">
                  Hindi (हिन्दी)
                </option>
                <option value="Marathi" className="bg-[var(--ink-900)] text-white">
                  Marathi (मराठी)
                </option>
              </select>
            </div>
          </div>

          <div className="hidden lg:block w-[1px] h-10 bg-[var(--ink-700)]" />

          {/* 4. Sort / View */}
          <div className="hidden md:flex items-center gap-3 shrink-0">
            <div className="w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white shrink-0">
              <SlidersHorizontal className="w-5 h-5 text-white/80" />
            </div>
            <div className="flex flex-col">
              <span className="text-[12px] font-medium text-[var(--text-on-dark-muted)]">
                Sort by
              </span>
              <select
                value={sortView}
                onChange={(e) => setSortView(e.target.value)}
                className="bg-transparent text-white text-[14px] font-medium outline-none cursor-pointer pr-4 appearance-none"
                style={{
                  backgroundImage:
                    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E\")",
                  backgroundRepeat: "no-repeat",
                  backgroundPosition: "right center",
                }}
              >
                <option value="Latest" className="bg-[var(--ink-900)] text-white">
                  Latest checks
                </option>
                <option value="Highest uncertainty" className="bg-[var(--ink-900)] text-white">
                  Highest uncertainty
                </option>
                <option value="Needs review" className="bg-[var(--ink-900)] text-white">
                  Needs review
                </option>
              </select>
            </div>
          </div>
        </div>

        {/* Right: Confidence Range Control per design.md §4.2 */}
        <div className="w-full xl:w-72 shrink-0 pt-2 xl:pt-0">
          <div className="flex justify-between items-center mb-1.5 text-[12px]">
            <span className="text-[var(--text-on-dark-muted)] font-medium">
              Confidence range
            </span>
            <span className="text-white font-mono font-medium">
              {Math.round(confidenceRange[0] * 100)}% – {Math.round(confidenceRange[1] * 100)}%
            </span>
          </div>

          {/* Interactive range slider track */}
          <div className="relative w-full h-5 flex items-center">
            {/* Base track */}
            <div className="w-full h-[2px] bg-[var(--ink-700)] rounded-full" />
            {/* Active filled track */}
            <div
              className="absolute h-[2px] bg-[var(--accent-sky)] rounded-full"
              style={{
                left: `${confidenceRange[0] * 100}%`,
                width: `${(confidenceRange[1] - confidenceRange[0]) * 100}%`,
              }}
            />
            {/* Left handle */}
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={confidenceRange[0]}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                if (val <= confidenceRange[1] - 0.1) {
                  onConfidenceRangeChange([val, confidenceRange[1]]);
                }
              }}
              className="absolute w-full h-2 opacity-0 cursor-pointer pointer-events-auto"
            />
            {/* Right handle */}
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={confidenceRange[1]}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                if (val >= confidenceRange[0] + 0.1) {
                  onConfidenceRangeChange([confidenceRange[0], val]);
                }
              }}
              className="absolute w-full h-2 opacity-0 cursor-pointer pointer-events-auto"
            />
            {/* Visible custom handle discs */}
            <div
              className="absolute w-4 h-4 rounded-full bg-[var(--accent-sky)] ring-2 ring-white/20 -ml-2 pointer-events-none transition-transform hover:scale-110"
              style={{ left: `${confidenceRange[0] * 100}%` }}
            />
            <div
              className="absolute w-4 h-4 rounded-full bg-[var(--accent-sky)] ring-2 ring-white/20 -ml-2 pointer-events-none transition-transform hover:scale-110"
              style={{ left: `${confidenceRange[1] * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

