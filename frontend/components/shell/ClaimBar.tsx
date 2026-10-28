"use client";

import { useState, useCallback } from "react";
import {
  Search,
  Image,
  Film,
  Mic,
  FileText,
  ChevronDown,
  SlidersHorizontal,
} from "lucide-react";

/**
 * ClaimBar.tsx — The dark "search row" below the top bar (design 4.2).
 * Contains claim input, media type, language, sort/view selectors, and a
 * confidence range slider.
 */

interface ClaimBarProps {
  onClaimChange?: (value: string) => void;
  onMediaTypeChange?: (value: string) => void;
  onLanguageChange?: (value: string) => void;
  onSortChange?: (value: string) => void;
  onRangeChange?: (min: number, max: number) => void;
}

const MEDIA_TYPES = [
  { value: "image", label: "Image", icon: Image },
  { value: "video", label: "Video", icon: Film },
  { value: "audio", label: "Audio", icon: Mic },
  { value: "text", label: "Text only", icon: FileText },
];

const LANGUAGES = [
  "Auto-detect",
  "English",
  "Hindi",
  "Marathi",
];

const SORTS = [
  "Latest",
  "Highest uncertainty",
  "Needs review",
];

export default function ClaimBar({
  onClaimChange,
  onMediaTypeChange,
  onLanguageChange,
  onSortChange,
  onRangeChange,
}: ClaimBarProps) {
  const [claim, setClaim] = useState("");
  const [mediaType, setMediaType] = useState("");
  const [language, setLanguage] = useState("");
  const [sort, setSort] = useState("Latest");
  const [rangeMin, setRangeMin] = useState(20);
  const [rangeMax, setRangeMax] = useState(90);

  /* Dropdown state */
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const toggleDropdown = useCallback(
    (name: string) => {
      setOpenDropdown((prev) => (prev === name ? null : name));
    },
    []
  );

  const divider = (
    <div
      className="w-px h-10 shrink-0"
      style={{ background: "var(--ink-700)" }}
    />
  );

  return (
    <div
      className="relative flex flex-wrap items-center gap-4 px-8 lg:px-14 py-5"
      style={{ background: "var(--ink-900)" }}
    >
      {/* 1 ── Claim input */}
      <div className="flex items-center gap-3 flex-1 min-w-[200px]">
        <div
          className="w-12 h-12 rounded-full shrink-0 flex items-center justify-center"
          style={{ border: "1px solid var(--ink-700)" }}
        >
          <Search size={18} strokeWidth={1.5} color="var(--text-on-dark)" />
        </div>
        <input
          type="text"
          placeholder="Paste a claim or caption"
          value={claim}
          onChange={(e) => {
            setClaim(e.target.value);
            onClaimChange?.(e.target.value);
          }}
          className="bg-transparent border-none outline-none text-[15px] font-medium w-full placeholder:text-[var(--text-on-dark-muted)]"
          style={{
            color: "var(--text-on-dark)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        />
      </div>

      {divider}

      {/* 2 ── Media type dropdown */}
      <div className="relative">
        <button
          onClick={() => toggleDropdown("media")}
          className="flex items-center gap-2 py-2 text-sm font-medium"
          style={{
            color: mediaType
              ? "var(--text-on-dark)"
              : "var(--text-on-dark-muted)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          <span>{mediaType || "Media type"}</span>
          <ChevronDown size={14} strokeWidth={1.5} />
        </button>
        {openDropdown === "media" && (
          <div
            className="absolute top-full mt-2 left-0 py-2 rounded-xl z-50 min-w-[160px]"
            style={{
              background: "var(--ink-800)",
              border: "1px solid var(--ink-700)",
            }}
          >
            {MEDIA_TYPES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => {
                  setMediaType(label);
                  onMediaTypeChange?.(value);
                  setOpenDropdown(null);
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-left transition-colors duration-100"
                style={{
                  color:
                    mediaType === label
                      ? "var(--text-on-dark)"
                      : "var(--text-on-dark-muted)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "var(--ink-700)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <Icon size={16} strokeWidth={1.5} />
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="hidden sm:block">{divider}</div>

      {/* 3 ── Language dropdown */}
      <div className="relative">
        <button
          onClick={() => toggleDropdown("lang")}
          className="flex items-center gap-2 py-2 text-sm font-medium"
          style={{
            color: language
              ? "var(--text-on-dark)"
              : "var(--text-on-dark-muted)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          <span>{language || "Language"}</span>
          <ChevronDown size={14} strokeWidth={1.5} />
        </button>
        {openDropdown === "lang" && (
          <div
            className="absolute top-full mt-2 left-0 py-2 rounded-xl z-50 min-w-[160px]"
            style={{
              background: "var(--ink-800)",
              border: "1px solid var(--ink-700)",
            }}
          >
            {LANGUAGES.map((lang) => (
              <button
                key={lang}
                onClick={() => {
                  setLanguage(lang);
                  onLanguageChange?.(lang);
                  setOpenDropdown(null);
                }}
                className="w-full px-4 py-2.5 text-sm text-left transition-colors duration-100"
                style={{
                  color:
                    language === lang
                      ? "var(--text-on-dark)"
                      : "var(--text-on-dark-muted)",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "var(--ink-700)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                {lang}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="hidden sm:block">{divider}</div>

      {/* 4 ── Sort/View */}
      <div className="relative">
        <button
          onClick={() => toggleDropdown("sort")}
          className="flex items-center gap-2 py-2 text-sm font-medium"
          style={{
            color: "var(--text-on-dark)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          <SlidersHorizontal size={16} strokeWidth={1.5} />
          <span>{sort}</span>
          <ChevronDown size={14} strokeWidth={1.5} />
        </button>
        {openDropdown === "sort" && (
          <div
            className="absolute top-full mt-2 left-0 py-2 rounded-xl z-50 min-w-[180px]"
            style={{
              background: "var(--ink-800)",
              border: "1px solid var(--ink-700)",
            }}
          >
            {SORTS.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setSort(s);
                  onSortChange?.(s);
                  setOpenDropdown(null);
                }}
                className="w-full px-4 py-2.5 text-sm text-left transition-colors duration-100"
                style={{
                  color:
                    sort === s
                      ? "var(--text-on-dark)"
                      : "var(--text-on-dark-muted)",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "var(--ink-700)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="hidden lg:block">{divider}</div>

      {/* 5 ── Confidence range */}
      <div className="hidden lg:flex flex-col gap-1 min-w-[200px]">
        <div className="flex items-center justify-between text-xs font-medium">
          <span style={{ color: "var(--text-on-dark-muted)" }}>
            Confidence range
          </span>
          <span style={{ color: "var(--text-on-dark)" }}>
            {rangeMin}% – {rangeMax}%
          </span>
        </div>
        <div className="relative h-5 flex items-center">
          {/* Track */}
          <div
            className="absolute w-full h-[2px] rounded-full"
            style={{ background: "var(--ink-700)" }}
          />
          {/* Fill */}
          <div
            className="absolute h-[2px] rounded-full"
            style={{
              background: "var(--accent-sky)",
              left: `${rangeMin}%`,
              right: `${100 - rangeMax}%`,
            }}
          />
          {/* Min handle */}
          <input
            type="range"
            min={0}
            max={100}
            value={rangeMin}
            onChange={(e) => {
              const val = Math.min(Number(e.target.value), rangeMax - 5);
              setRangeMin(val);
              onRangeChange?.(val, rangeMax);
            }}
            className="absolute w-full appearance-none bg-transparent z-10 cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:shadow-sm"
            style={
              {
                "--tw-ring-color": "var(--accent-sky)",
              } as React.CSSProperties
            }
            aria-label="Minimum confidence"
          />
          {/* Max handle */}
          <input
            type="range"
            min={0}
            max={100}
            value={rangeMax}
            onChange={(e) => {
              const val = Math.max(Number(e.target.value), rangeMin + 5);
              setRangeMax(val);
              onRangeChange?.(rangeMin, val);
            }}
            className="absolute w-full appearance-none bg-transparent z-20 cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:shadow-sm"
            aria-label="Maximum confidence"
          />
        </div>
      </div>

      {/* Close dropdowns on outside click */}
      {openDropdown && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setOpenDropdown(null)}
        />
      )}
    </div>
  );
}
