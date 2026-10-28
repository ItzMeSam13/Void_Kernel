"use client";

import { AlertTriangle } from "lucide-react";
import { useState } from "react";

/**
 * VideoTimeline.tsx — Timeline strip with flagged timestamps (design 4.6).
 * For video reports: horizontal strip with small markers at flagged timestamps.
 */

interface TimelineMarker {
  timestamp: number; // seconds
  label: string;
}

interface VideoTimelineProps {
  duration?: number; // total seconds
  markers: TimelineMarker[];
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function VideoTimeline({
  duration = 120,
  markers,
}: VideoTimelineProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (markers.length === 0) return null;

  return (
    <div
      className="rounded-[24px] p-5"
      style={{
        background: "var(--card)",
        border: "1px solid var(--ink-200)",
      }}
    >
      <h3
        className="text-[15px] font-medium mb-4"
        style={{
          color: "var(--ink-400)",
          fontFamily: "var(--font-inter), sans-serif",
        }}
      >
        Video timeline
      </h3>

      {/* Timeline strip */}
      <div className="relative w-full h-10 mb-3">
        {/* Track */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-full h-[3px] rounded-full"
          style={{ background: "var(--ink-200)" }}
        />

        {/* Time labels */}
        <span
          className="absolute top-full mt-1 left-0 text-[11px] font-medium"
          style={{
            color: "var(--ink-400)",
            fontFamily: "var(--font-ibm-plex-mono), monospace",
          }}
        >
          0:00
        </span>
        <span
          className="absolute top-full mt-1 right-0 text-[11px] font-medium"
          style={{
            color: "var(--ink-400)",
            fontFamily: "var(--font-ibm-plex-mono), monospace",
          }}
        >
          {formatTime(duration)}
        </span>

        {/* Markers */}
        {markers.map((marker, i) => {
          const pct = (marker.timestamp / duration) * 100;
          const isHovered = hoveredIdx === i;
          return (
            <div
              key={i}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10"
              style={{ left: `${pct}%` }}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              {/* Marker dot */}
              <button
                className="w-5 h-5 rounded-full flex items-center justify-center transition-transform duration-150"
                style={{
                  background: "var(--status-signal)",
                  transform: isHovered ? "scale(1.3)" : "scale(1)",
                }}
                aria-label={`Flag at ${formatTime(marker.timestamp)}: ${marker.label}`}
              >
                <AlertTriangle size={10} strokeWidth={2} color="white" />
              </button>

              {/* Tooltip */}
              {isHovered && (
                <div
                  className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 whitespace-nowrap px-3 py-2 rounded-lg text-[12px] font-medium"
                  style={{
                    background: "var(--ink-900)",
                    color: "var(--text-on-dark)",
                    fontFamily: "var(--font-inter), sans-serif",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-ibm-plex-mono), monospace",
                    }}
                  >
                    {formatTime(marker.timestamp)}
                  </span>
                  {" — "}
                  {marker.label}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Marker list */}
      <div className="mt-6 space-y-2">
        {markers.map((marker, i) => (
          <div
            key={i}
            className="flex items-center gap-3 text-[13px] font-medium"
            style={{
              color: "var(--text-on-light)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: "var(--status-signal)" }}
            />
            <span
              style={{
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                color: "var(--ink-500)",
              }}
            >
              {formatTime(marker.timestamp)}
            </span>
            <span>{marker.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
