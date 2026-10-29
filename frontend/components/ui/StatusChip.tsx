"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  MinusCircle,
  Clock,
  Loader2,
} from "lucide-react";
import { VerdictTone } from "@/lib/types";

interface StatusChipProps {
  tone?: VerdictTone;
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

export function StatusChip({
  tone = "clear",
  label,
  size = "md",
  className = "",
}: StatusChipProps) {
  let displayLabel = label;
  let Icon = CheckCircle2;
  let bgStyle = "";
  let textStyle = "";
  let iconColor = "";

  switch (tone) {
    case "signal":
      displayLabel = label || "Signal detected";
      Icon = AlertTriangle;
      bgStyle = "bg-[#E8667A]/15 border-[#E8667A]/30";
      textStyle = "text-[#C7384E]";
      iconColor = "text-[#C7384E]";
      break;

    case "clear":
      displayLabel = label || "No strong signal";
      Icon = CheckCircle2;
      bgStyle = "bg-[#2FAE8F]/15 border-[#2FAE8F]/30";
      textStyle = "text-[#1C826A]";
      iconColor = "text-[#1C826A]";
      break;

    case "inconclusive":
      displayLabel = label || "Inconclusive";
      Icon = HelpCircle;
      bgStyle = "bg-[#E0A23A]/15 border-[#E0A23A]/30";
      textStyle = "text-[#B37817]";
      iconColor = "text-[#B37817]";
      break;

    case "na":
      displayLabel = label || "Not assessed";
      Icon = MinusCircle;
      bgStyle = "bg-[#8E8E99]/15 border-[#8E8E99]/30";
      textStyle = "text-[#62626D]";
      iconColor = "text-[#62626D]";
      break;

    case "running":
      displayLabel = label || "Checking…";
      Icon = Loader2;
      bgStyle = "bg-[#7CC4F8]/15 border-[#7CC4F8]/30";
      textStyle = "text-[#1B7EC5]";
      iconColor = "text-[#1B7EC5] animate-spin";
      break;

    case "queued":
      displayLabel = label || "In queue";
      Icon = Clock;
      bgStyle = "bg-[var(--ink-400)]/15 border-[var(--ink-400)]/30";
      textStyle = "text-[var(--ink-500)]";
      iconColor = "text-[var(--ink-500)]";
      break;
  }

  const sizeClasses =
    size === "sm"
      ? "text-[12px] py-1 px-2.5 gap-1.5"
      : "text-[13px] py-1.5 px-3.5 gap-2";

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border transition-colors select-none ${sizeClasses} ${bgStyle} ${textStyle} ${className}`}
    >
      <Icon className={`w-3.5 h-3.5 shrink-0 ${iconColor}`} strokeWidth={2} />
      <span>{displayLabel}</span>
    </span>
  );
}

