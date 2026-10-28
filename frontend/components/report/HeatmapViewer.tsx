"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

/**
 * HeatmapViewer.tsx — Heatmap overlay card for image analysis (design 4.6).
 * Shows the submitted image with an adjustable opacity heatmap overlay,
 * and a toggle to view the original. Uses a placeholder when no real
 * heatmap data is available.
 */

interface HeatmapViewerProps {
  imageUrl?: string;
  heatmapUrl?: string;
  altText?: string;
}

export default function HeatmapViewer({
  imageUrl,
  heatmapUrl,
  altText = "Media with anomaly heatmap overlay",
}: HeatmapViewerProps) {
  const [opacity, setOpacity] = useState(40);
  const [showOriginal, setShowOriginal] = useState(false);

  const hasHeatmap = !!heatmapUrl;

  return (
    <div
      className="rounded-[24px] overflow-hidden"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
      }}
    >
      {/* Image area */}
      <div className="relative w-full aspect-video overflow-hidden rounded-t-[24px]">
        {/* Base image or placeholder */}
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={altText}
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ background: "var(--pastel-grey)" }}
          >
            <div className="text-center">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--ink-400)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mx-auto mb-3"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="m21 15-5-5L5 21" />
              </svg>
              <p
                className="text-[13px] font-medium"
                style={{
                  color: "var(--ink-400)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                Image preview not available
              </p>
            </div>
          </div>
        )}

        {/* Heatmap overlay */}
        {hasHeatmap && !showOriginal && (
          <img
            src={heatmapUrl}
            alt="Anomaly heatmap overlay"
            className="absolute inset-0 w-full h-full object-cover pointer-events-none"
            style={{ opacity: opacity / 100 }}
          />
        )}

        {/* Placeholder heatmap gradient (for demo) */}
        {!hasHeatmap && !showOriginal && (
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "radial-gradient(ellipse at 35% 60%, rgba(232,102,122,0.5) 0%, transparent 50%), radial-gradient(ellipse at 70% 30%, rgba(224,162,58,0.3) 0%, transparent 40%)",
              opacity: opacity / 100,
            }}
          />
        )}
      </div>

      {/* Controls */}
      <div className="p-5">
        <div className="flex items-center justify-between gap-4">
          {/* Opacity slider */}
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span
                className="text-[13px] font-medium"
                style={{
                  color: "var(--ink-400)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                Overlay opacity
              </span>
              <span
                className="text-[13px] font-medium"
                style={{
                  color: "var(--text-on-light)",
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                }}
              >
                {opacity}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="w-full h-[2px] appearance-none rounded-full cursor-pointer"
              style={{
                background: `linear-gradient(to right, var(--accent-sky) ${opacity}%, var(--ink-200) ${opacity}%)`,
              }}
              aria-label="Heatmap overlay opacity"
            />
          </div>

          {/* Toggle original */}
          <button
            onClick={() => setShowOriginal(!showOriginal)}
            className="flex items-center gap-2 px-4 py-2 rounded-full text-[13px] font-medium transition-colors duration-150"
            style={{
              border: "1px solid var(--ink-200)",
              color: "var(--text-on-light)",
              fontFamily: "var(--font-inter), sans-serif",
              background: showOriginal ? "var(--ink-100)" : "transparent",
            }}
          >
            {showOriginal ? (
              <EyeOff size={14} strokeWidth={1.5} />
            ) : (
              <Eye size={14} strokeWidth={1.5} />
            )}
            {showOriginal ? "Show heatmap" : "Show original"}
          </button>
        </div>

        {/* Text alt for heatmap */}
        <p
          className="mt-3 text-[12px] font-medium"
          style={{
            color: "var(--ink-400)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          Highest anomaly near the lower-left of the image
        </p>
      </div>
    </div>
  );
}
