"use client";

import React from "react";

interface PillProps {
  children: React.ReactNode;
  variant?: "outline" | "solid" | "chip";
  className?: string;
  icon?: React.ReactNode;
}

export function Pill({
  children,
  variant = "outline",
  className = "",
  icon,
}: PillProps) {
  let styleClasses = "";

  if (variant === "outline") {
    // 1px --ink-900 at 35% opacity outline, transparent fill, 13px 500
    styleClasses =
      "border border-[var(--ink-900)]/30 text-[var(--text-on-light)] bg-transparent hover:bg-[var(--ink-900)]/5";
  } else if (variant === "solid") {
    styleClasses =
      "bg-white text-[var(--text-on-light)] border border-[var(--ink-200)] shadow-xs";
  } else if (variant === "chip") {
    styleClasses =
      "bg-[var(--ink-100)] text-[var(--ink-500)] border border-transparent";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium leading-none select-none transition-colors ${styleClasses} ${className}`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
}

