"use client";

/**
 * Pill.tsx — Small tag/badge element (design section 4).
 * Used for counts, labels, inline metadata.
 * Outlined by default, with optional filled variant.
 */

interface PillProps {
  children: React.ReactNode;
  variant?: "outlined" | "filled";
  color?: string;
  bgColor?: string;
  className?: string;
}

export default function Pill({
  children,
  variant = "outlined",
  color,
  bgColor,
  className = "",
}: PillProps) {
  const styles: React.CSSProperties =
    variant === "outlined"
      ? {
          border: "1px solid var(--ink-200)",
          background: "transparent",
          color: color ?? "var(--text-on-light)",
          fontFamily: "var(--font-inter), sans-serif",
        }
      : {
          border: "none",
          background: bgColor ?? "var(--pastel-grey)",
          color: color ?? "var(--text-on-light)",
          fontFamily: "var(--font-inter), sans-serif",
        };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[13px] font-medium ${className}`}
      style={styles}
    >
      {children}
    </span>
  );
}
