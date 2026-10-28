"use client";

/**
 * PromoCard.tsx — Dark promo card in the left column (design 4.3).
 * Radius --r-lg, background --ink-900, noise texture, arc line art.
 */

import Button from "@/components/ui/Button";

export default function PromoCard() {
  return (
    <div
      className="relative noise-texture overflow-hidden p-8"
      style={{
        background: "var(--ink-900)",
        borderRadius: "var(--r-lg)",
      }}
    >
      {/* Thin arc line art */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        viewBox="0 0 320 280"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle
          cx="280"
          cy="40"
          r="120"
          stroke="rgba(255,255,255,0.18)"
          strokeWidth="1"
          fill="none"
        />
        <circle
          cx="-20"
          cy="240"
          r="90"
          stroke="rgba(255,255,255,0.12)"
          strokeWidth="1"
          fill="none"
        />
        <path
          d="M 50 20 Q 160 80 260 40"
          stroke="rgba(255,255,255,0.10)"
          strokeWidth="0.8"
          fill="none"
        />
      </svg>

      {/* Content */}
      <div className="relative z-10">
        <h2
          className="text-[34px] leading-[1.15] font-extrabold mb-8"
          style={{
            color: "var(--text-on-dark)",
            fontFamily: "var(--font-manrope), sans-serif",
            maxWidth: "100%",
          }}
        >
          Verify before you forward.
        </h2>

        <Button variant="accent" size="lg" className="w-full">
          Learn how it works
        </Button>
      </div>
    </div>
  );
}
