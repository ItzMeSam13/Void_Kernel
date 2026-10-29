"use client";

import React from "react";

export function Backdrop() {
  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none overflow-hidden z-0"
      style={{ backgroundColor: "var(--bg-backdrop)" }}
    >
      {/* Subtle thin geometric arcs and curves per design.md §3 */}
      <svg
        className="absolute w-full h-full"
        viewBox="0 0 1920 1080"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="1750"
          cy="120"
          r="480"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
        />
        <circle
          cx="1750"
          cy="120"
          r="720"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
          strokeDasharray="4 6"
        />
        <circle
          cx="100"
          cy="920"
          r="540"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
        />
        <path
          d="M -100 200 C 400 100, 700 600, 1100 450"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
        />
        <path
          d="M 800 1150 C 1200 950, 1600 1100, 2050 900"
          stroke="var(--bg-backdrop-line)"
          strokeWidth="1"
        />
      </svg>
    </div>
  );
}

