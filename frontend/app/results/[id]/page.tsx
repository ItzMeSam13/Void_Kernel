"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import AppShell from "@/components/shell/AppShell";
import AxisCard from "@/components/cards/AxisCard";
import EvidenceRow from "@/components/cards/EvidenceRow";
import ExplanationPanel from "@/components/report/ExplanationPanel";
import HeatmapViewer from "@/components/report/HeatmapViewer";
import VideoTimeline from "@/components/report/VideoTimeline";
import Drawer from "@/components/ui/Drawer";
import Button from "@/components/ui/Button";
import { DEMO_REPORTS } from "@/lib/demo-data";
import type { AxisKey, Finding } from "@/lib/types";
import { AXIS_META } from "@/lib/types";

/**
 * Results page — Four-axis report view (design 4.6).
 * Header + 2x2 axis grid + explanation + evidence list.
 */

const AXIS_KEYS: AxisKey[] = [
  "claim_veracity",
  "media_authenticity",
  "cross_modal_consistency",
  "historical_reuse",
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${d.getDate()} ${months[d.getMonth()]}, ${d.getFullYear()}`;
}

export default function ResultsPage() {
  const params = useParams();
  const id = params?.id as string;

  const [drawerAxis, setDrawerAxis] = useState<AxisKey | null>(null);

  // Find report (demo mode)
  const report = DEMO_REPORTS.find((r) => r.id === id) ?? DEMO_REPORTS[0];

  const drawerFinding: Finding | null = drawerAxis
    ? report.axes[drawerAxis]
    : null;

  return (
    <AppShell>
      <div className="px-5 md:px-8 lg:px-14 py-8 lg:py-12 max-w-[1200px] mx-auto">
        {/* Back link */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-[14px] font-medium mb-8 transition-opacity duration-150 hover:opacity-70"
          style={{
            color: "var(--ink-400)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          <ArrowLeft size={16} strokeWidth={1.5} />
          Back to checks
        </Link>

        {/* Report header */}
        <div
          className="rounded-[28px] p-8 mb-8"
          style={{
            background: "var(--card)",
            border: "1px solid var(--ink-200)",
          }}
        >
          <div className="flex flex-col md:flex-row md:items-start gap-6">
            {/* Media thumbnail placeholder */}
            <div
              className="w-full md:w-40 h-32 rounded-[20px] shrink-0 flex items-center justify-center text-[13px] font-medium"
              style={{
                background: "var(--pastel-grey)",
                color: "var(--ink-400)",
                fontFamily: "var(--font-inter), sans-serif",
              }}
            >
              {report.mediaType.charAt(0).toUpperCase() +
                report.mediaType.slice(1)}{" "}
              preview
            </div>

            <div className="flex-1">
              <h1
                className="text-[28px] leading-[32px] font-bold mb-3"
                style={{
                  fontFamily: "var(--font-manrope), sans-serif",
                  color: "var(--text-on-light)",
                  textWrap: "balance" as unknown as string,
                }}
              >
                {report.claimText}
              </h1>

              <div className="flex items-center gap-4 flex-wrap">
                <span
                  className="text-[13px] font-medium"
                  style={{
                    color: "var(--ink-400)",
                    fontFamily:
                      "var(--font-ibm-plex-mono), monospace",
                  }}
                >
                  {report.id}
                </span>
                <span
                  className="text-[13px] font-medium"
                  style={{
                    color: "var(--ink-400)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  {formatDate(report.createdAt)}
                </span>
                {report.source && (
                  <span
                    className="text-[13px] font-medium"
                    style={{
                      color: "var(--ink-400)",
                      fontFamily: "var(--font-inter), sans-serif",
                    }}
                  >
                    via {report.source}
                  </span>
                )}
                <span
                  className="text-[13px] font-medium"
                  style={{
                    color: "var(--ink-400)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  {report.language}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Demo data label */}
        <div
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[12px] font-medium mb-6"
          style={{
            background: "var(--pastel-pink)",
            color: "var(--text-on-light)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          Demo data
        </div>

        {/* Four-axis grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {AXIS_KEYS.map((key) => (
            <AxisCard
              key={key}
              axisKey={key}
              finding={report.axes[key]}
              onDetails={() => setDrawerAxis(key)}
            />
          ))}
        </div>

        {/* Explanation */}
        {report.explanation && (
          <div className="mb-8">
            <ExplanationPanel
              text={report.explanation}
              biasRegulatorRan={report.biasRegulatorRan}
            />
          </div>
        )}

        {/* Heatmap viewer (image reports) */}
        {report.mediaType === "image" && (
          <div className="mb-8">
            <h2
              className="text-[22px] font-bold mb-4"
              style={{
                fontFamily: "var(--font-manrope), sans-serif",
                color: "var(--text-on-light)",
              }}
            >
              Anomaly heatmap
            </h2>
            <HeatmapViewer
              imageUrl={report.mediaUrl}
              heatmapUrl={report.heatmapUrl}
            />
          </div>
        )}

        {/* Video timeline (video reports) */}
        {report.mediaType === "video" && report.videoTimeline && report.videoTimeline.length > 0 && (
          <div className="mb-8">
            <h2
              className="text-[22px] font-bold mb-4"
              style={{
                fontFamily: "var(--font-manrope), sans-serif",
                color: "var(--text-on-light)",
              }}
            >
              Flagged moments
            </h2>
            <VideoTimeline markers={report.videoTimeline} />
          </div>
        )}

        {/* Evidence list */}
        {report.evidenceItems.length > 0 && (
          <div>
            <h2
              className="text-[22px] font-bold mb-4"
              style={{
                fontFamily: "var(--font-manrope), sans-serif",
                color: "var(--text-on-light)",
              }}
            >
              Evidence
            </h2>
            <div className="space-y-4">
              {report.evidenceItems.map((item) => (
                <EvidenceRow key={item.id} item={item} />
              ))}
            </div>
          </div>
        )}

        {/* Empty evidence state */}
        {report.evidenceItems.length === 0 && (
          <div
            className="rounded-[24px] p-10 flex flex-col items-center text-center"
            style={{
              background: "var(--card)",
              border: "1px solid var(--ink-200)",
            }}
          >
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center mb-4"
              style={{ background: "var(--pastel-grey)" }}
            >
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--ink-400)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M8 12h8" />
              </svg>
            </div>
            <p
              className="text-[17px] font-medium mb-2"
              style={{
                color: "var(--text-on-light)",
                fontFamily: "var(--font-inter), sans-serif",
              }}
            >
              No external evidence found
            </p>
            <p
              className="text-[14px] font-medium"
              style={{
                color: "var(--ink-400)",
                fontFamily: "var(--font-inter), sans-serif",
              }}
            >
              The analysis relied on media signals only.
            </p>
          </div>
        )}
      </div>

      {/* Detail drawer */}
      <Drawer
        open={drawerAxis !== null}
        onClose={() => setDrawerAxis(null)}
        title={drawerAxis ? AXIS_META[drawerAxis].label : undefined}
      >
        {drawerAxis && drawerFinding && (
          <div className="space-y-6">
            {/* Status */}
            <div>
              <p
                className="text-[14px] font-medium mb-2"
                style={{
                  color: "var(--ink-400)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                Status
              </p>
              <p
                className="text-[17px] font-semibold"
                style={{
                  color: "var(--text-on-light)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                {drawerFinding.status === "signal_detected" &&
                  "One or more detector signals were raised."}
                {drawerFinding.status === "no_strong_signal" &&
                  "No supporting signals contradicted this axis."}
                {drawerFinding.status === "inconclusive" &&
                  "Available evidence was insufficient for a determination."}
                {drawerFinding.status === "not_assessed" &&
                  `Not assessed: ${(drawerFinding as { reason: string }).reason}`}
                {drawerFinding.status === "checking" &&
                  "Analysis is in progress…"}
                {drawerFinding.status === "in_queue" &&
                  "Waiting in the processing queue."}
              </p>
            </div>

            {/* Confidence */}
            {drawerFinding.status !== "not_assessed" && (
              <div>
                <p
                  className="text-[14px] font-medium mb-2"
                  style={{
                    color: "var(--ink-400)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  Confidence
                </p>
                <p
                  className="text-[24px] font-medium"
                  style={{
                    color: "var(--text-on-light)",
                    fontFamily:
                      "var(--font-ibm-plex-mono), monospace",
                  }}
                >
                  {(
                    (drawerFinding as { confidence: number }).confidence * 100
                  ).toFixed(0)}
                  %
                </p>
                <p
                  className="text-[12px] font-medium mt-1"
                  style={{
                    color: "var(--ink-400)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  How strongly the available evidence agrees. It is not a
                  guarantee.
                </p>
              </div>
            )}

            {/* Technical details */}
            {drawerFinding.status !== "not_assessed" &&
              (drawerFinding as { tags: string[] }).tags.length > 0 && (
                <div>
                  <p
                    className="text-[14px] font-medium mb-3"
                    style={{
                      color: "var(--ink-400)",
                      fontFamily: "var(--font-inter), sans-serif",
                    }}
                  >
                    Technical details
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(drawerFinding as { tags: string[] }).tags.map(
                      (tag, i) => (
                        <span
                          key={i}
                          className="inline-block px-3.5 py-2 rounded-full text-[13px] font-medium"
                          style={{
                            border: "1px solid var(--ink-200)",
                            color: "var(--text-on-light)",
                            fontFamily:
                              "var(--font-ibm-plex-mono), monospace",
                          }}
                        >
                          {tag}
                        </span>
                      )
                    )}
                  </div>
                </div>
              )}
          </div>
        )}
      </Drawer>
    </AppShell>
  );
}
