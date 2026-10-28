"use client";

/**
 * Backdrop.tsx — Decorative lavender backdrop with thin white arc line art.
 * Placed with position: fixed, z-index: 0, aria-hidden.
 */

export default function Backdrop() {
  return (
    <div
      className="fixed inset-0 z-0 overflow-hidden"
      style={{ background: "var(--bg-backdrop)" }}
      aria-hidden="true"
    >
      <svg
        className="absolute w-full h-full"
        viewBox="0 0 1440 900"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* Large arc top-right */}
        <circle
          cx="1200"
          cy="-100"
          r="500"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
          fill="none"
        />
        {/* Medium arc bottom-left */}
        <circle
          cx="-80"
          cy="800"
          r="400"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
          fill="none"
        />
        {/* Small arc center */}
        <circle
          cx="720"
          cy="450"
          r="280"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="0.5"
          fill="none"
        />
        {/* Thin arc top-left */}
        <path
          d="M -100 300 Q 200 100 500 250"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="0.8"
          fill="none"
        />
        {/* Thin arc bottom-right */}
        <path
          d="M 900 700 Q 1100 600 1400 750"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="0.8"
          fill="none"
        />
      </svg>
    </div>
  );
}
