"use client";

import React from "react";
import { Backdrop } from "./Backdrop";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative min-h-screen py-8 md:py-14 px-4 sm:px-8 lg:px-12 flex justify-center">
      {/* Decorative backdrop background */}
      <Backdrop />

      {/* Main app container per design.md §3 */}
      <div
        className="relative z-10 w-full max-w-[1720px] rounded-[32px] md:rounded-[40px] overflow-hidden bg-[var(--sheet)] flex flex-col border border-white/60 transition-all duration-300"
        style={{
          boxShadow: "0 30px 80px rgba(20, 20, 40, 0.18)",
        }}
      >
        {children}
      </div>
    </div>
  );
}

