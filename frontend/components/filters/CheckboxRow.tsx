"use client";

import { Check } from "lucide-react";

/**
 * CheckboxRow.tsx — Rounded-square checkbox + label row (design 4.3).
 * 24px checkbox, radius 7px. Checked = filled ink-900 + white check.
 */

interface CheckboxRowProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export default function CheckboxRow({
  label,
  checked,
  onChange,
}: CheckboxRowProps) {
  return (
    <label
      className="flex items-center gap-3 h-[42px] cursor-pointer group"
      style={{ fontFamily: "var(--font-inter), sans-serif" }}
    >
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className="w-6 h-6 rounded-[7px] flex items-center justify-center shrink-0 transition-colors duration-150"
        style={{
          background: checked ? "var(--ink-900)" : "transparent",
          border: checked
            ? "none"
            : "1.5px solid var(--ink-200)",
        }}
      >
        {checked && (
          <Check size={14} strokeWidth={2.5} color="white" />
        )}
      </button>
      <span
        className="text-[17px] font-medium"
        style={{ color: "var(--text-on-light)" }}
      >
        {label}
      </span>
    </label>
  );
}
