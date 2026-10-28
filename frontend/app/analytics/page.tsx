"use client";

import { useState } from "react";
import AppShell from "@/components/shell/AppShell";
import MetricCard from "@/components/cards/MetricCard";
import { DEMO_EVAL_DATA } from "@/lib/demo-data";
import type { SliceRow } from "@/lib/types";

/**
 * Analytics page — Module 8 eval reports (design 4.10).
 * Metric cards, slice table, and risk-vs-coverage chart.
 * Uses demo data; labels it clearly as "Demo data".
 */

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/* ── Slice table ──────────────────────────────────────────── */

function SliceTable({ slices }: { slices: SliceRow[] }) {
  const dimensions = Array.from(
    new Set(slices.map((s) => s.dimension))
  );

  return (
    <div
      className="rounded-[28px] overflow-hidden"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
      }}
    >
      <div className="p-6">
        <h3
          className="text-[22px] font-bold mb-4"
          style={{
            fontFamily: "var(--font-manrope), sans-serif",
            color: "var(--text-on-light)",
          }}
        >
          Performance by slice
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--ink-200)",
                }}
              >
                {["Dimension", "Value", "Precision", "Recall", "FPR", "n"].map(
                  (h) => (
                    <th
                      key={h}
                      className="pb-3 pr-4 text-[13px] font-medium"
                      style={{
                        color: "var(--ink-400)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {dimensions.map((dim) => {
                const rows = slices.filter((s) => s.dimension === dim);
                return rows.map((row, i) => (
                  <tr
                    key={`${dim}-${row.value}`}
                    className="transition-colors duration-100"
                    style={{
                      borderBottom: "1px solid var(--ink-200)",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "var(--ink-100)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <td
                      className="py-3 pr-4 text-[14px] font-semibold"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      {i === 0 ? dim : ""}
                    </td>
                    <td
                      className="py-3 pr-4 text-[14px] font-medium"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      {row.value}
                    </td>
                    <td
                      className="py-3 pr-4 text-[14px] font-medium"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily:
                          "var(--font-ibm-plex-mono), monospace",
                      }}
                    >
                      {pct(row.precision)}
                    </td>
                    <td
                      className="py-3 pr-4 text-[14px] font-medium"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily:
                          "var(--font-ibm-plex-mono), monospace",
                      }}
                    >
                      {pct(row.recall)}
                    </td>
                    <td
                      className="py-3 pr-4 text-[14px] font-medium"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily:
                          "var(--font-ibm-plex-mono), monospace",
                      }}
                    >
                      {pct(row.fpr)}
                    </td>
                    <td
                      className="py-3 text-[14px] font-medium"
                      style={{
                        color: "var(--ink-400)",
                        fontFamily:
                          "var(--font-ibm-plex-mono), monospace",
                      }}
                    >
                      {row.n}
                    </td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ── Risk vs Coverage chart (SVG) ─────────────────────────── */

function RiskCoverageChart({
  data,
}: {
  data: { risk: number; coverage: number }[];
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  /* Chart dimensions */
  const width = 600;
  const height = 300;
  const padding = { top: 20, right: 30, bottom: 50, left: 55 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  /* Scale helpers */
  const xScale = (v: number) => padding.left + v * plotW;
  const yScale = (v: number) => padding.top + (1 - v) * plotH;

  /* Build polyline points */
  const points = data
    .map((d) => `${xScale(d.risk)},${yScale(d.coverage)}`)
    .join(" ");

  /* Build area path */
  const areaPath = `M ${xScale(data[0].risk)},${yScale(data[0].coverage)} ${data
    .slice(1)
    .map((d) => `L ${xScale(d.risk)},${yScale(d.coverage)}`)
    .join(" ")} L ${xScale(data[data.length - 1].risk)},${yScale(0)} L ${xScale(data[0].risk)},${yScale(0)} Z`;

  return (
    <div
      className="rounded-[28px] overflow-hidden"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
      }}
    >
      <div className="p-6">
        <h3
          className="text-[22px] font-bold mb-4"
          style={{
            fontFamily: "var(--font-manrope), sans-serif",
            color: "var(--text-on-light)",
          }}
        >
          Risk vs. Coverage
        </h3>

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full"
          style={{ maxHeight: 320 }}
          role="img"
          aria-label="Risk versus coverage trade-off chart"
        >
          {/* Baseline */}
          <line
            x1={padding.left}
            y1={yScale(0)}
            x2={xScale(1)}
            y2={yScale(0)}
            stroke="var(--ink-200)"
            strokeWidth="1"
          />
          <line
            x1={padding.left}
            y1={yScale(0)}
            x2={padding.left}
            y2={padding.top}
            stroke="var(--ink-200)"
            strokeWidth="1"
          />

          {/* Y grid labels */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
            <g key={v}>
              <text
                x={padding.left - 10}
                y={yScale(v) + 4}
                textAnchor="end"
                fontSize="11"
                fontFamily="var(--font-ibm-plex-mono), monospace"
                fill="var(--ink-500)"
              >
                {(v * 100).toFixed(0)}%
              </text>
              {v > 0 && (
                <line
                  x1={padding.left}
                  y1={yScale(v)}
                  x2={xScale(1)}
                  y2={yScale(v)}
                  stroke="var(--ink-200)"
                  strokeWidth="0.5"
                  strokeDasharray="4,4"
                  opacity="0.5"
                />
              )}
            </g>
          ))}

          {/* X labels */}
          {[0, 0.2, 0.4, 0.6, 0.8, 1.0].map((v) => (
            <text
              key={v}
              x={xScale(v)}
              y={height - padding.bottom + 25}
              textAnchor="middle"
              fontSize="11"
              fontFamily="var(--font-ibm-plex-mono), monospace"
              fill="var(--ink-500)"
            >
              {(v * 100).toFixed(0)}%
            </text>
          ))}

          {/* Axis labels */}
          <text
            x={width / 2}
            y={height - 5}
            textAnchor="middle"
            fontSize="12"
            fontFamily="var(--font-inter), sans-serif"
            fill="var(--ink-400)"
            fontWeight="500"
          >
            Risk tolerance
          </text>
          <text
            x={15}
            y={height / 2}
            textAnchor="middle"
            fontSize="12"
            fontFamily="var(--font-inter), sans-serif"
            fill="var(--ink-400)"
            fontWeight="500"
            transform={`rotate(-90, 15, ${height / 2})`}
          >
            Coverage
          </text>

          {/* Area fill */}
          <path
            d={areaPath}
            fill="var(--accent-sky)"
            opacity="0.12"
          />

          {/* Line */}
          <polyline
            points={points}
            fill="none"
            stroke="var(--accent-sky)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points */}
          {data.map((d, i) => (
            <g key={i}>
              <circle
                cx={xScale(d.risk)}
                cy={yScale(d.coverage)}
                r={hovered === i ? 6 : 4}
                fill="var(--accent-sky)"
                stroke="white"
                strokeWidth="2"
                className="transition-all duration-150 cursor-pointer"
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
              />
              {hovered === i && (
                <g>
                  <rect
                    x={xScale(d.risk) - 45}
                    y={yScale(d.coverage) - 35}
                    width="90"
                    height="24"
                    rx="6"
                    fill="var(--ink-900)"
                  />
                  <text
                    x={xScale(d.risk)}
                    y={yScale(d.coverage) - 19}
                    textAnchor="middle"
                    fontSize="11"
                    fontFamily="var(--font-ibm-plex-mono), monospace"
                    fill="white"
                  >
                    R:{(d.risk * 100).toFixed(0)}% C:
                    {(d.coverage * 100).toFixed(0)}%
                  </text>
                </g>
              )}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

/* ── Page component ───────────────────────────────────────── */

export default function AnalyticsPage() {
  const evalData = DEMO_EVAL_DATA;

  return (
    <AppShell>
      <div className="px-5 md:px-8 lg:px-14 py-8 lg:py-12 max-w-[1400px] mx-auto">
        {/* Page header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h1
              className="text-[40px] leading-[44px] font-extrabold tracking-[-0.02em]"
              style={{
                fontFamily: "var(--font-manrope), sans-serif",
                color: "var(--text-on-light)",
              }}
            >
              Analytics
            </h1>
          </div>
        </div>

        {/* Demo data label */}
        {evalData.isDemoData && (
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[12px] font-medium mb-8"
            style={{
              background: "var(--pastel-pink)",
              color: "var(--text-on-light)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            Demo data
          </div>
        )}

        {/* Metric cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {evalData.metrics.map((m) => (
            <MetricCard key={m.module} metrics={m} />
          ))}
        </div>

        {/* Slice table */}
        <div className="mb-8">
          <SliceTable slices={evalData.slices} />
        </div>

        {/* Risk vs Coverage chart */}
        <div className="mb-8">
          <RiskCoverageChart data={evalData.riskCoverage} />
        </div>
      </div>
    </AppShell>
  );
}
