"use client";

import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  MinusCircle,
  Loader2,
  Clock,
} from "lucide-react";
import type { VerdictState } from "@/lib/types";

/**
 * StatusChip.tsx — Pill with dot/icon, label text, and tinted background (design 4.7).
 */

const STATUS_CONFIG: Record<
  VerdictState,
  {
    label: string;
    icon: React.ElementType;
    color: string;
    bgOpacity: string;
  }
> = {
  signal_detected: {
    label: "Signal detected",
    icon: AlertTriangle,
    color: "var(--status-signal)",
    bgOpacity: "0.14",
  },
  no_strong_signal: {
    label: "No strong signal",
    icon: CheckCircle2,
    color: "var(--status-clear)",
    bgOpacity: "0.14",
  },
  inconclusive: {
    label: "Inconclusive",
    icon: HelpCircle,
    color: "var(--status-inconclusive)",
    bgOpacity: "0.14",
  },
  not_assessed: {
    label: "Not assessed",
    icon: MinusCircle,
    color: "var(--status-na)",
    bgOpacity: "0.14",
  },
  checking: {
    label: "Checking…",
    icon: Loader2,
    color: "var(--accent-sky)",
    bgOpacity: "0.14",
  },
  in_queue: {
    label: "In queue",
    icon: Clock,
    color: "var(--ink-400)",
    bgOpacity: "0.14",
  },
};

interface StatusChipProps {
  status: VerdictState;
  className?: string;
}

export default function StatusChip({ status, className = "" }: StatusChipProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const isSpinner = status === "checking";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium ${className}`}
      style={{
        background: `color-mix(in srgb, ${config.color} ${parseFloat(config.bgOpacity) * 100}%, transparent)`,
        color: config.color,
        fontFamily: "var(--font-inter), sans-serif",
      }}
    >
      <Icon
        size={14}
        strokeWidth={1.5}
        className={isSpinner ? "animate-spin" : ""}
      />
      {config.label}
    </span>
  );
}
