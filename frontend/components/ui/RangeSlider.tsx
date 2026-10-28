"use client";

import { useState, useCallback } from "react";

/**
 * RangeSlider.tsx — Dual-handle range slider (design 4.2).
 * 2px track with sky-blue fill between handles, 20px round handles.
 */

interface RangeSliderProps {
  min?: number;
  max?: number;
  defaultMin?: number;
  defaultMax?: number;
  step?: number;
  gap?: number;
  label?: string;
  onChange?: (min: number, max: number) => void;
}

export default function RangeSlider({
  min = 0,
  max = 100,
  defaultMin = 20,
  defaultMax = 90,
  step = 1,
  gap = 5,
  label = "Confidence range",
  onChange,
}: RangeSliderProps) {
  const [rangeMin, setRangeMin] = useState(defaultMin);
  const [rangeMax, setRangeMax] = useState(defaultMax);

  const handleMinChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = Math.min(Number(e.target.value), rangeMax - gap);
      setRangeMin(val);
      onChange?.(val, rangeMax);
    },
    [rangeMax, gap, onChange]
  );

  const handleMaxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = Math.max(Number(e.target.value), rangeMin + gap);
      setRangeMax(val);
      onChange?.(rangeMin, val);
    },
    [rangeMin, gap, onChange]
  );

  const range = max - min;
  const leftPct = ((rangeMin - min) / range) * 100;
  const rightPct = ((max - rangeMax) / range) * 100;

  return (
    <div className="flex flex-col gap-1 min-w-[200px]">
      <div className="flex items-center justify-between text-xs font-medium">
        <span style={{ color: "var(--text-on-dark-muted)" }}>{label}</span>
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
            left: `${leftPct}%`,
            right: `${rightPct}%`,
          }}
        />
        {/* Min handle */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={rangeMin}
          onChange={handleMinChange}
          className="range-slider-thumb absolute w-full appearance-none bg-transparent z-10 cursor-pointer"
          aria-label={`Minimum ${label}`}
        />
        {/* Max handle */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={rangeMax}
          onChange={handleMaxChange}
          className="range-slider-thumb absolute w-full appearance-none bg-transparent z-20 cursor-pointer"
          aria-label={`Maximum ${label}`}
        />
      </div>
    </div>
  );
}
