"use client";

import React, { useState } from "react";
import { Eye, EyeOff, Sliders, Layers } from "lucide-react";

interface HeatmapViewerProps {
  originalImageUrl?: string | null;
  heatmapImageUrl?: string | null;
  anomalyDescription?: string;
}

export function HeatmapViewer({
  originalImageUrl,
  heatmapImageUrl,
  anomalyDescription,
}: HeatmapViewerProps) {
  const [opacity, setOpacity] = useState(40);
  const [showOriginalOnly, setShowOriginalOnly] = useState(false);

  return (
    <div className="bg-white rounded-[28px] border border-[var(--ink-200)] p-6 select-none flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-[var(--accent-sky-600)]" />
          <h4 className="font-display font-bold text-[18px] text-[var(--text-on-light)]">
            Spatial Anomaly Localization
          </h4>
        </div>

        {/* Toggle original vs overlay */}
        <button
          onClick={() => setShowOriginalOnly(!showOriginalOnly)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[var(--ink-200)] hover:bg-[var(--ink-100)] text-[12px] font-medium text-[var(--ink-500)] transition-colors"
        >
          {showOriginalOnly ? (
            <>
              <Eye className="w-3.5 h-3.5" />
              <span>Show heatmap</span>
            </>
          ) : (
            <>
              <EyeOff className="w-3.5 h-3.5" />
              <span>Hide heatmap</span>
            </>
          )}
        </button>
      </div>

      {/* Media Canvas */}
      <div className="relative w-full h-72 sm:h-80 rounded-[20px] overflow-hidden bg-[var(--ink-900)] flex items-center justify-center border border-[var(--ink-200)]">
        {/* Placeholder or real image */}
        {originalImageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={originalImageUrl}
            alt="Source media frame"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-[#1b2838] to-[#0a111a] flex items-center justify-center text-white/40 text-sm">
            <span>Camera Sensor Frame Preview</span>
          </div>
        )}

        {/* Simulated or real heatmap overlay layer */}
        {!showOriginalOnly && (
          heatmapImageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={heatmapImageUrl}
              alt="Forensic heatmap anomaly overlay"
              className="absolute inset-0 w-full h-full object-contain pointer-events-none transition-opacity duration-150"
              style={{ opacity: opacity / 100 }}
            />
          ) : (
            <div
              className="absolute inset-0 pointer-events-none transition-opacity duration-150"
              style={{
                opacity: opacity / 100,
                background:
                  "radial-gradient(circle at 45% 40%, rgba(232,102,122,0.9) 0%, rgba(224,162,58,0.6) 25%, rgba(124,196,248,0.2) 60%, transparent 80%)",
              }}
            />
          )
        )}

        {/* Localized boundary box */}
        {!showOriginalOnly && (
          <div
            className="absolute w-32 h-32 border-2 border-dashed border-[#E8667A] rounded-lg pointer-events-none flex items-start justify-end p-1"
            style={{ left: "35%", top: "25%", opacity: opacity / 100 }}
          >
            <span className="bg-[#E8667A] text-white text-[10px] font-mono px-1 rounded">
              0.87
            </span>
          </div>
        )}
      </div>

      {/* Opacity Control & Description */}
      <div className="mt-4 pt-3 border-t border-[var(--ink-200)] space-y-2">
        <div className="flex items-center justify-between text-[13px]">
          <span className="text-[var(--ink-500)] flex items-center gap-1.5 font-medium">
            <Sliders className="w-3.5 h-3.5" />
            Heatmap opacity
          </span>
          <span className="font-mono text-[var(--ink-500)]">{opacity}%</span>
        </div>

        <input
          type="range"
          min="0"
          max="100"
          value={opacity}
          disabled={showOriginalOnly}
          onChange={(e) => setOpacity(parseInt(e.target.value, 10))}
          className="w-full h-1.5 bg-[var(--ink-200)] rounded-full appearance-none cursor-pointer accent-[var(--ink-900)]"
        />

        <p className="text-[13px] text-[var(--ink-500)] mt-2">
          {anomalyDescription ||
            "Highest spatial anomaly localized in quadrant Q2 (face-boundary blending seam detected by ViT attention rollout)."}
        </p>
      </div>
    </div>
  );
}

