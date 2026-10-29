"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Share2,
  AlertTriangle,
  Film,
  Image as ImageIcon,
  Mic,
  Code,
} from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { AxisCard } from "@/components/cards/AxisCard";
import { ExplanationPanel } from "@/components/report/ExplanationPanel";
import { HeatmapViewer } from "@/components/report/HeatmapViewer";
import { VideoTimeline } from "@/components/report/VideoTimeline";
import { EvidenceRow } from "@/components/cards/EvidenceRow";
import { Drawer } from "@/components/ui/Drawer";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { getJobStatus } from "@/lib/api";
import { Report } from "@/lib/types";

function ResultsSkeleton() {
  return (
    <div className="bg-[#F5F1E8] min-h-screen p-4 sm:p-6 lg:p-8 flex flex-col lg:flex-row gap-6 max-w-[1780px] mx-auto antialiased">
      <Sidebar activeTab="verifications" />
      <div className="flex-1 min-w-0 bg-white rounded-[28px] border border-[#E8E3D7] p-6 sm:p-10 shadow-xs flex flex-col gap-8">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="w-11 h-11 rounded-full bg-[#F5F2EB] border border-[#E8E3D7] flex items-center justify-center text-[#6B6B75] hover:bg-[#EAE6DC]"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="space-y-1">
            <h2 className="text-2xl font-display font-bold text-[#111114]">
              Loading multi-modal forensic evidence…
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    </div>
  );
}

function ResultsContent() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCitation, setSelectedCitation] = useState<number | null>(null);

  // Technical drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerAxis, setDrawerAxis] = useState<string>("technical");

  useEffect(() => {
    let isMounted = true;

    async function loadReport() {
      if (!id) return;
      try {
        const data = await getJobStatus(id);
        if (isMounted && data) {
          setReport(data);
        }
      } catch (err) {
        console.error("Failed to load report:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadReport();

    const interval = setInterval(() => {
      if (report && (report.status === "queued" || report.status === "processing")) {
        loadReport();
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [id, report]);

  if (loading || !report) {
    return <ResultsSkeleton />;
  }

  const MediaIcon =
    report.media_type === "video"
      ? Film
      : report.media_type === "image"
      ? ImageIcon
      : Mic;

  return (
    <div className="bg-[#F5F1E8] min-h-screen p-4 sm:p-6 lg:p-8 flex flex-col lg:flex-row gap-6 max-w-[1780px] mx-auto antialiased">
      <Sidebar activeTab="verifications" />

      <main className="flex-1 min-w-0 bg-white rounded-[28px] border border-[#E8E3D7] p-6 sm:p-10 shadow-xs flex flex-col gap-10">
        <div className="w-full space-y-10">
          {/* Header Block per design.md §4.6 */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-[var(--ink-200)]">
            <div className="flex items-start gap-4 flex-1">
              <Link
                href="/"
                className="w-12 h-12 rounded-full bg-white border border-[var(--ink-200)] flex items-center justify-center text-[var(--ink-700)] hover:bg-[var(--ink-100)] transition-transform active:scale-95 shrink-0 shadow-xs"
                title="Back to checks"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>

              {/* Media Thumbnail + Claim Title */}
              <div className="space-y-2 flex-1">
                <div className="flex flex-wrap items-center gap-2.5 text-[13px]">
                  <span className="font-mono font-medium text-[var(--ink-400)]">
                    REPORT {report.job_id}
                  </span>
                  <span className="text-[var(--ink-200)]">·</span>
                  <span className="font-mono text-[var(--ink-400)]">
                    SHA256: {report.sha256.slice(0, 12)}…
                  </span>
                  <span className="text-[var(--ink-200)]">·</span>
                  <span className="text-[var(--ink-500)] flex items-center gap-1 font-medium">
                    <MediaIcon className="w-3.5 h-3.5 text-[var(--ink-400)]" />
                    {report.media_type.toUpperCase()} ({report.language})
                  </span>
                  <span className="text-[var(--ink-200)]">·</span>
                  <span className="text-[var(--ink-500)]">{report.created_at}</span>
                </div>

                <h1 className="font-display font-extrabold text-[28px] sm:text-[34px] leading-[1.2] text-[var(--text-on-light)]">
                  &ldquo;{report.claim_text}&rdquo;
                </h1>

                {/* Recompression Caveat Warning Banner */}
                {report.recompression_caveat && (
                  <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#E0A23A]/15 border border-[#E0A23A]/30 text-[#B37817] text-[13px] font-medium">
                    <AlertTriangle className="w-4 h-4" />
                    <span>
                      Confidence caveat active: heavy recompression detected in source encoding
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3 shrink-0 self-end md:self-auto">
              <button
                onClick={() => {
                  setDrawerAxis("technical");
                  setDrawerOpen(true);
                }}
                className="h-11 px-5 rounded-full border border-[var(--ink-200)] hover:bg-white text-[13px] font-semibold text-[var(--ink-700)] flex items-center gap-2 transition-colors cursor-pointer shadow-xs"
              >
                <Code className="w-4 h-4 text-[var(--ink-400)]" />
                <span>Technical Trace</span>
              </button>

              <button
                onClick={() => {
                  navigator.clipboard?.writeText(window.location.href);
                  alert("Report link copied to clipboard!");
                }}
                className="w-11 h-11 rounded-full bg-white border border-[var(--ink-200)] flex items-center justify-center text-[var(--ink-700)] hover:bg-[var(--ink-100)] transition-colors shadow-xs"
                title="Share report"
              >
                <Share2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* 4-Axis Grid per design.md §4.6 & §2.2
              NEVER collapse into one score or overall fake/real banner */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-bold text-[22px] text-[var(--text-on-light)]">
                Independent Verification Axes
              </h3>
              <span className="text-[13px] text-[var(--ink-400)] italic">
                Four distinct signals, never averaged into a single verdict
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <AxisCard
                axisType="claim_veracity"
                finding={report.axes.claim_veracity}
                onOpenDrawer={() => {
                  setDrawerAxis("claim_veracity");
                  setDrawerOpen(true);
                }}
              />
              <AxisCard
                axisType="media_authenticity"
                finding={report.axes.media_authenticity}
                onOpenDrawer={() => {
                  setDrawerAxis("media_authenticity");
                  setDrawerOpen(true);
                }}
              />
              <AxisCard
                axisType="cross_modal_consistency"
                finding={report.axes.cross_modal_consistency}
                onOpenDrawer={() => {
                  setDrawerAxis("cross_modal_consistency");
                  setDrawerOpen(true);
                }}
              />
              <AxisCard
                axisType="historical_reuse"
                finding={report.axes.historical_reuse}
                onOpenDrawer={() => {
                  setDrawerAxis("historical_reuse");
                  setDrawerOpen(true);
                }}
              />
            </div>
          </div>

          {/* Explanation Panel with interactive citations per design.md §4.6 */}
          <ExplanationPanel
            explanation={report.explanation}
            onSelectCitation={(idx) => {
              setSelectedCitation(idx);
              const el = document.getElementById(`evidence-item-${idx}`);
              el?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
            activeCitation={selectedCitation}
          />

          {/* Visual Forensics Inspection: Heatmap (for Image) or Timeline (for Video/Audio) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <HeatmapViewer
              anomalyDescription={
                report.axes.media_authenticity.status === "ok"
                  ? report.axes.media_authenticity.concrete_evidence[0]
                  : undefined
              }
            />
            <VideoTimeline
              segments={report.flagged_segments}
              durationSec={47.8}
            />
          </div>

          {/* Evidence List per design.md §4.6 */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-[22px] text-[var(--text-on-light)]">
                Corroborating & Contradicting Evidence ({report.evidence.length})
              </h3>
              <span className="text-[13px] text-[var(--ink-400)] font-mono">
                Adversarial search + Google Fact Check API
              </span>
            </div>

            <div className="space-y-4">
              {report.evidence.map((item, idx) => (
                <div key={item.id} id={`evidence-item-${idx}`}>
                  <EvidenceRow
                    item={item}
                    citationIndex={idx}
                    isHighlighted={selectedCitation === idx}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Technical Evidence Drawer per design.md §4.6 */}
      <Drawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={
          drawerAxis === "technical"
            ? "Forensic Execution Trace"
            : drawerAxis === "media_authenticity"
            ? "Media Authenticity Details"
            : drawerAxis === "claim_veracity"
            ? "Claim Veracity Details"
            : drawerAxis === "cross_modal_consistency"
            ? "Cross-Modal Consistency Details"
            : "Historical Reuse Details"
        }
        subtitle={`Report ID: ${report.job_id}`}
      >
        <div className="space-y-6 text-[14px]">
          {/* Concrete Forensic Evidence */}
          {report.axes.media_authenticity.status === "ok" && (
            <div className="p-4 rounded-[16px] bg-[var(--sheet)] border border-[var(--ink-200)] space-y-2">
              <h5 className="font-semibold text-[var(--text-on-light)] text-[15px]">
                Concrete Detector Signals
              </h5>
              <ul className="list-disc list-inside space-y-1 text-[var(--ink-500)] text-[13px]">
                {report.axes.media_authenticity.concrete_evidence.map((ev, i) => (
                  <li key={i}>{ev}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Model Weights and Pipeline Configuration */}
          <div className="p-4 rounded-[16px] bg-[var(--sheet)] border border-[var(--ink-200)] space-y-2">
            <h5 className="font-semibold text-[var(--text-on-light)] text-[15px]">
              Evaluated Models & Checkpoints
            </h5>
            <div className="space-y-1.5 text-[12px] font-mono text-[var(--ink-500)]">
              <p>• Audio Deepfake: mo-thecreator/Deepfake-audio-detection (Wav2Vec2)</p>
              <p>• Speech Transcription: Systran/faster-whisper-small (CTranslate2)</p>
              <p>• Image Forensics: Smaug-72B & ManTraNet Spatial ResNet50</p>
              <p>• Visual-Textual: OpenAI CLIP ViT-B/32 & PaddleOCR</p>
              <p>• Evidence NLI: Microsoft DeBERTa-v3-large Stance Judge</p>
            </div>
          </div>

          {/* Raw JSON Contract */}
          <div>
            <h5 className="font-semibold text-[var(--text-on-light)] text-[15px] mb-2">
              Raw Pydantic JSON Contract
            </h5>
            <pre className="p-4 rounded-[16px] bg-[var(--ink-900)] text-[#7CC4F8] font-mono text-[11px] overflow-x-auto max-h-96">
              {JSON.stringify(report, null, 2)}
            </pre>
          </div>
        </div>
      </Drawer>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<ResultsSkeleton />}>
      <ResultsContent />
    </Suspense>
  );
}
