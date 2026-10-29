"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  Info,
} from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { DEMO_EVAL_METRICS } from "@/lib/api";
import { EvalMetric } from "@/lib/types";

export default function AnalyticsPage() {
  const [selectedModule, setSelectedModule] = useState<string>("image");

  const currentMetric: EvalMetric =
    DEMO_EVAL_METRICS.find((m) => m.module === selectedModule) ||
    DEMO_EVAL_METRICS[0];

  return (
    <div className="bg-[#F5F1E8] min-h-screen p-4 sm:p-6 lg:p-8 flex flex-col lg:flex-row gap-6 max-w-[1780px] mx-auto antialiased">
      <Sidebar activeTab="activity" />

      <main className="flex-1 min-w-0 bg-white rounded-[28px] border border-[#E8E3D7] p-6 sm:p-10 shadow-xs flex flex-col gap-10">
        <div className="w-full space-y-10">
          {/* Header Block */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-[var(--ink-200)]">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="w-12 h-12 rounded-full bg-white border border-[var(--ink-200)] flex items-center justify-center text-[var(--ink-700)] hover:bg-[var(--ink-100)] transition-transform active:scale-95 shadow-xs"
                title="Back to checks"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[12px] font-semibold text-[var(--accent-sky-600)] uppercase tracking-wider">
                    Module 8 Performance Suite
                  </span>
                  {/* Mandatory "Demo data" chip per design.md §4.10 & §10 */}
                  <span className="px-2.5 py-0.5 rounded-full bg-[#E0A23A]/15 border border-[#E0A23A]/30 text-[#B37817] text-[11px] font-mono font-medium">
                    Demo data
                  </span>
                </div>
                <h1 className="font-display font-extrabold text-[32px] sm:text-[38px] text-[var(--text-on-light)] tracking-tight">
                  Quantitative Forensics Evaluation
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-2 text-[13px] text-[var(--ink-500)] bg-white px-4 py-2 rounded-full border border-[var(--ink-200)] shadow-xs">
              <Clock className="w-4 h-4 text-[var(--ink-400)]" />
              <span>Evaluated: {currentMetric.last_evaluated}</span>
            </div>
          </div>

          {/* Module Selector Pills */}
          <div className="flex flex-wrap gap-2.5">
            {DEMO_EVAL_METRICS.map((mod) => (
              <button
                key={mod.module}
                onClick={() => setSelectedModule(mod.module)}
                className={`h-11 px-5 rounded-full text-[14px] font-semibold transition-all cursor-pointer select-none ${
                  selectedModule === mod.module
                    ? "bg-[#0E0E10] text-white shadow-sm"
                    : "bg-white text-[#484852] border border-[#E8E3D7] hover:bg-[#FAF8F5]"
                }`}
              >
                <span>{mod.module_name.split("—")[1]?.trim() || mod.module_name}</span>
              </button>
            ))}
          </div>

          {/* Top 4 Metric Cards Grid in Pastel Panels per design.md §4.10 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* 1. Accuracy */}
            <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2">
              <div className="bg-[var(--pastel-mint)] rounded-[24px] p-6 h-full flex flex-col justify-between min-h-[160px]">
                <span className="text-[13px] font-medium text-[var(--text-on-light)]/75 uppercase tracking-wide">
                  Model Accuracy
                </span>
                <div className="my-2">
                  <span className="font-display font-extrabold text-[42px] text-[var(--text-on-light)] tracking-tight">
                    {(currentMetric.accuracy * 100).toFixed(1)}%
                  </span>
                </div>
                <span className="text-[12px] font-mono text-[var(--text-on-light)]/70">
                  n = {currentMetric.sample_count} evaluated
                </span>
              </div>
            </div>

            {/* 2. F1 Score */}
            <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2">
              <div className="bg-[var(--pastel-sky)] rounded-[24px] p-6 h-full flex flex-col justify-between min-h-[160px]">
                <span className="text-[13px] font-medium text-[var(--text-on-light)]/75 uppercase tracking-wide">
                  F1 Balanced Score
                </span>
                <div className="my-2">
                  <span className="font-display font-extrabold text-[42px] text-[var(--text-on-light)] tracking-tight">
                    {currentMetric.f1_score.toFixed(3)}
                  </span>
                </div>
                <span className="text-[12px] font-mono text-[var(--text-on-light)]/70">
                  Harmonic precision/recall
                </span>
              </div>
            </div>

            {/* 3. False Positive Rate (with mandatory 95% interval per §4.10) */}
            <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2">
              <div className="bg-[var(--pastel-peach)] rounded-[24px] p-6 h-full flex flex-col justify-between min-h-[160px]">
                <span className="text-[13px] font-medium text-[var(--text-on-light)]/75 uppercase tracking-wide">
                  False Positive Rate
                </span>
                <div className="my-2">
                  <span className="font-display font-extrabold text-[42px] text-[var(--text-on-light)] tracking-tight">
                    {(currentMetric.false_positive_rate * 100).toFixed(1)}%
                  </span>
                </div>
                {/* 95% interval per design.md §4.10: "FPR 7.1% (4–13%), n=140" */}
                <span className="text-[12px] font-mono text-[var(--text-on-light)]/70">
                  95% CI ({currentMetric.fpr_ci_95})
                </span>
              </div>
            </div>

            {/* 4. Latency p95 */}
            <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-2">
              <div className="bg-[var(--pastel-lavender)] rounded-[24px] p-6 h-full flex flex-col justify-between min-h-[160px]">
                <span className="text-[13px] font-medium text-[var(--text-on-light)]/75 uppercase tracking-wide">
                  p95 Latency
                </span>
                <div className="my-2">
                  <span className="font-display font-extrabold text-[42px] text-[var(--text-on-light)] tracking-tight">
                    {currentMetric.latency_ms_p95}ms
                  </span>
                </div>
                <span className="text-[12px] font-mono text-[var(--text-on-light)]/70">
                  CPU / GPU inference
                </span>
              </div>
            </div>
          </div>

          {/* Module Methodology & Dataset Notes */}
          <div className="p-6 rounded-[24px] bg-white border border-[var(--ink-200)] flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-[var(--ink-100)] flex items-center justify-center text-[var(--ink-900)] shrink-0">
              <Info className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-display font-bold text-[17px] text-[var(--text-on-light)] mb-1">
                Evaluation Protocol & Dataset Composition
              </h4>
              <p className="text-[14px] text-[var(--ink-500)] leading-relaxed">
                {currentMetric.notes}
              </p>
            </div>
          </div>

          {/* Slices Table per design.md §4.10 (language, bitrate, compression) */}
          <div className="bg-white rounded-[28px] border border-[var(--ink-200)] overflow-hidden">
            <div className="p-6 border-b border-[var(--ink-200)] flex items-center justify-between">
              <div>
                <h3 className="font-display font-bold text-[20px] text-[var(--text-on-light)]">
                  Robustness & Disaggregated Slices
                </h3>
                <p className="text-[13px] text-[var(--ink-400)] mt-0.5">
                  Performance across codecs, bitrates, compression thresholds, and durations
                </p>
              </div>
              <span className="font-mono text-[12px] text-[var(--ink-400)]">
                Slice breakdown: {currentMetric.slices.length} subsets
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[14px]">
                <thead className="bg-[var(--sheet)] border-b border-[var(--ink-200)] text-[12px] font-semibold text-[var(--ink-500)] uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-6">Slice Category</th>
                    <th className="py-3.5 px-6">Slice Condition</th>
                    <th className="py-3.5 px-6 font-mono text-right">Sample N</th>
                    <th className="py-3.5 px-6 font-mono text-right">Accuracy</th>
                    <th className="py-3.5 px-6 font-mono text-right">False Positive Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--ink-100)]">
                  {currentMetric.slices.map((sl, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-[var(--ink-100)]/50 transition-colors"
                    >
                      <td className="py-4 px-6 font-medium text-[var(--text-on-light)]">
                        {sl.category}
                      </td>
                      <td className="py-4 px-6 text-[var(--ink-500)] font-mono">
                        {sl.value}
                      </td>
                      <td className="py-4 px-6 font-mono text-right text-[var(--ink-700)]">
                        {sl.sample_size}
                      </td>
                      <td className="py-4 px-6 font-mono font-semibold text-right text-[#1C826A]">
                        {(sl.accuracy * 100).toFixed(1)}%
                      </td>
                      <td className="py-4 px-6 font-mono text-right text-[var(--ink-700)]">
                        {(sl.fpr * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

