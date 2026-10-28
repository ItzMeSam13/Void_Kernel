"use client";

import type { ModuleMetrics } from "@/lib/types";

/**
 * MetricCard.tsx — Analytics metric card (design 4.10).
 * Shows precision, recall, FPR, latency with n and 95% CI.
 */

/* Map module names to pastel colors */
const MODULE_PASTELS: Record<string, string> = {
  "Claim Veracity": "var(--pastel-peach)",
  "Media Authenticity": "var(--pastel-mint)",
  "Cross-modal Consistency": "var(--pastel-lavender)",
  "Historical Reuse": "var(--pastel-sky)",
};

interface MetricCardProps {
  metrics: ModuleMetrics;
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export default function MetricCard({ metrics }: MetricCardProps) {
  const pastel =
    MODULE_PASTELS[metrics.module] ?? "var(--pastel-grey)";

  const rows = [
    {
      label: "Precision",
      value: pct(metrics.precision),
    },
    {
      label: "Recall",
      value: pct(metrics.recall),
    },
    {
      label: "FPR",
      value: `${pct(metrics.fpr)} (${pct(metrics.ci95Low)}–${pct(metrics.ci95High)})`,
      sub: `n=${metrics.n}`,
    },
    {
      label: "Latency p50",
      value: `${metrics.latencyP50}ms`,
    },
    {
      label: "Latency p95",
      value: `${metrics.latencyP95}ms`,
    },
  ];

  return (
    <div
      className="rounded-[28px] transition-all duration-200 hover:-translate-y-0.5"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
        padding: 8,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow =
          "0 8px 24px rgba(20,20,40,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      <div className="rounded-[24px] p-5" style={{ background: pastel }}>
        <h3
          className="text-[22px] font-bold mb-4"
          style={{
            fontFamily: "var(--font-manrope), sans-serif",
            color: "var(--text-on-light)",
          }}
        >
          {metrics.module}
        </h3>

        <div className="space-y-2">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex items-center justify-between"
            >
              <span
                className="text-[14px] font-medium"
                style={{
                  color: "var(--ink-500)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                {row.label}
              </span>
              <div className="text-right">
                <span
                  className="text-[15px] font-medium"
                  style={{
                    color: "var(--text-on-light)",
                    fontFamily:
                      "var(--font-ibm-plex-mono), monospace",
                  }}
                >
                  {row.value}
                </span>
                {row.sub && (
                  <span
                    className="ml-2 text-[12px]"
                    style={{ color: "var(--ink-400)" }}
                  >
                    {row.sub}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
