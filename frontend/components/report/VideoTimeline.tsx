"use client";

import React, { useState } from "react";
import { Play, Pause, AlertCircle, Clock } from "lucide-react";
import { FlaggedSegment } from "@/lib/types";

interface VideoTimelineProps {
  durationSec?: number;
  segments: FlaggedSegment[];
}

export function VideoTimeline({
  durationSec = 47.8,
  segments,
}: VideoTimelineProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(6.2);

  return (
    <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-6 select-none flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-[var(--accent-sky-600)]" />
          <h4 className="font-display font-bold text-[18px] text-[var(--text-on-light)]">
            Temporal Segment Analysis
          </h4>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-7 h-7 rounded-full bg-[var(--ink-100)] hover:bg-[var(--ink-200)] flex items-center justify-center text-[var(--ink-700)] transition-colors"
            aria-label={isPlaying ? "Pause playback" : "Play preview"}
          >
            {isPlaying ? (
              <Pause className="w-3.5 h-3.5 fill-current" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
            )}
          </button>
          <span className="font-mono text-[13px] text-[var(--ink-500)]">
            {currentTime.toFixed(1)}s / {durationSec.toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Video timeline track with flagged markers */}
      <div className="relative w-full h-12 bg-[var(--ink-100)] rounded-[14px] overflow-hidden p-2 flex items-center border border-[var(--ink-200)]">
        {/* Flagged segments overlaid on timeline */}
        {segments.map((seg, idx) => {
          const leftPct = (seg.start_sec / durationSec) * 100;
          const widthPct = ((seg.end_sec - seg.start_sec) / durationSec) * 100;
          return (
            <div
              key={idx}
              className="absolute top-1 bottom-1 bg-[#E8667A]/30 border border-[#E8667A] rounded-md flex items-center justify-center cursor-pointer group hover:bg-[#E8667A]/50 transition-colors"
              style={{ left: `${leftPct}%`, width: `${Math.max(widthPct, 4)}%` }}
              onClick={() => setCurrentTime(seg.start_sec)}
              title={`${seg.label} (${seg.start_sec}s - ${seg.end_sec}s)`}
            >
              <span className="hidden sm:inline text-[10px] font-bold text-[#C7384E] truncate px-1">
                {seg.score.toFixed(2)}
              </span>
            </div>
          );
        })}

        {/* Current playback cursor */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-[var(--ink-900)] z-10 transition-all pointer-events-none"
          style={{ left: `${(currentTime / durationSec) * 100}%` }}
        >
          <div className="w-3 h-3 bg-[var(--ink-900)] rounded-full -ml-1 -mt-1 shadow-sm" />
        </div>
      </div>

      {/* Segment Cards List */}
      <div className="mt-4 space-y-2">
        <span className="text-[12px] font-semibold text-[var(--ink-400)] uppercase tracking-wider block">
          Flagged Intervals ({segments.length})
        </span>

        {segments.length === 0 ? (
          <p className="text-[13px] text-[var(--ink-400)] italic py-2">
            No temporal manipulation markers detected across analyzed windows.
          </p>
        ) : (
          segments.map((seg, idx) => (
            <div
              key={idx}
              onClick={() => setCurrentTime(seg.start_sec)}
              className="flex items-center justify-between p-3 rounded-[16px] bg-[var(--sheet)] hover:bg-[var(--ink-100)] transition-colors cursor-pointer border border-[var(--ink-200)]"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#E8667A]/15 flex items-center justify-center text-[#C7384E]">
                  <AlertCircle className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-[14px] font-semibold text-[var(--text-on-light)] block">
                    {seg.label}
                  </span>
                  <span className="text-[12px] text-[var(--ink-500)]">
                    {seg.description}
                  </span>
                </div>
              </div>

              <div className="text-right shrink-0">
                <span className="font-mono text-[13px] font-semibold text-[var(--ink-900)] block">
                  {seg.start_sec.toFixed(1)}s – {seg.end_sec.toFixed(1)}s
                </span>
                <span className="text-[11px] font-mono text-[#C7384E]">
                  score {(seg.score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

