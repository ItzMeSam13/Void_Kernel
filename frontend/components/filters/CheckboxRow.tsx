"use client";

import React from "react";
import { Check } from "lucide-react";

interface CheckboxRowProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  count?: number;
}

export function CheckboxRow({
  id,
  label,
  checked,
  onChange,
  count,
}: CheckboxRowProps) {
  return (
    <label
      htmlFor={id}
      className="flex items-center justify-between h-[42px] px-1 cursor-pointer select-none group transition-colors"
    >
      <div className="flex items-center gap-3.5">
        {/* Custom 24px rounded-square checkbox (radius 7px) */}
        <div
          className={`w-6 h-6 rounded-[7px] flex items-center justify-center transition-all ${
            checked
              ? "bg-[var(--ink-900)] text-white shadow-xs"
              : "border-[1.5px] border-[var(--ink-200)] bg-white group-hover:border-[var(--ink-400)]"
          }`}
        >
          {checked && <Check className="w-3.5 h-3.5 stroke-[2.5]" />}
        </div>

        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />

        {/* Label 17px --text-on-light per design.md §4.3 */}
        <span className="text-[16px] text-[var(--text-on-light)] font-normal group-hover:text-black">
          {label}
        </span>
      </div>

      {count !== undefined && (
        <span className="text-[13px] font-mono text-[var(--ink-400)]">
          {count}
        </span>
      )}
    </label>
  );
}

