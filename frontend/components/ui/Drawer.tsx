"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";

/**
 * Drawer.tsx — Right-hand slide-out drawer (design section 5).
 * 250ms slide from right with 45% black overlay.
 */

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export default function Drawer({ open, onClose, title, children }: DrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  /* Focus trap: close on Escape */
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) {
      document.addEventListener("keydown", handleKey);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100]">
      {/* Overlay */}
      <div
        className="absolute inset-0 transition-opacity duration-250"
        style={{ background: "rgba(0,0,0,0.45)" }}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        ref={drawerRef}
        className="absolute top-0 right-0 h-full w-full max-w-[560px] overflow-y-auto"
        style={{
          background: "var(--sheet)",
          animation: "slideIn 250ms var(--ease-out) both",
        }}
        role="dialog"
        aria-label={title || "Detail drawer"}
      >
        {/* Header */}
        <div
          className="sticky top-0 z-10 flex items-center justify-between px-8 py-6"
          style={{
            background: "var(--sheet)",
            borderBottom: "1px solid var(--ink-200)",
          }}
        >
          {title && (
            <h2
              className="text-xl font-bold"
              style={{
                fontFamily: "var(--font-manrope), sans-serif",
                color: "var(--text-on-light)",
              }}
            >
              {title}
            </h2>
          )}
          <button
            onClick={onClose}
            className="w-11 h-11 rounded-full flex items-center justify-center transition-colors duration-150"
            style={{ border: "1px solid var(--ink-200)" }}
            aria-label="Close drawer"
          >
            <X size={18} strokeWidth={1.5} color="var(--text-on-light)" />
          </button>
        </div>

        {/* Content */}
        <div className="p-8">{children}</div>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}
