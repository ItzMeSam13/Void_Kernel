"use client";

import TopBar from "./TopBar";
import ClaimBar from "./ClaimBar";
import Backdrop from "./Backdrop";

/**
 * AppShell.tsx — The main application container (design section 3).
 * Rounded app shell on the lavender backdrop. Dark top block + light sheet.
 */

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <>
      <Backdrop />

      {/* App shell container */}
      <div
        className="relative z-10 mx-auto w-full flex flex-col min-h-screen"
        style={{
          maxWidth: 1720,
          borderRadius: "var(--r-xl)",
          overflow: "hidden",
          boxShadow: "0 30px 80px rgba(20,20,40,0.18)",
        }}
      >
        {/* Dark top block (top bar + claim bar) */}
        <TopBar />
        <ClaimBar />

        {/* Light sheet */}
        <main
          className="flex-1"
          style={{
            background: "var(--sheet)",
          }}
        >
          {children}
        </main>

        {/* Footer */}
        <footer
          className="px-8 lg:px-14 py-6 text-center text-xs font-medium"
          style={{
            background: "var(--sheet)",
            color: "var(--ink-400)",
            fontFamily: "var(--font-inter), sans-serif",
            borderTop: "1px solid var(--ink-200)",
          }}
        >
          Results are evidence signals, not proof.
        </footer>
      </div>
    </>
  );
}
