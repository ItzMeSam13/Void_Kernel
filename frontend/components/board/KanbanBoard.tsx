"use client";

import React from "react";
import Link from "next/link";
import {
  MoreVertical,
  Calendar,
  MessageSquare,
  Paperclip,
  Film,
} from "lucide-react";

export interface BoardCardItem {
  id: string;
  column: "to_do" | "in_progress" | "under_review" | "ready";
  tags: { label: string; color: "purple" | "orange" | "yellow" | "mint" | "sky" }[];
  title: string;
  description: string;
  date: string;
  hasMediaPreview?: boolean;
  mediaType?: "video" | "audio" | "image";
  anomalyScore?: number;
  commentsCount: number;
  evidenceCount: number;
  analyst: { name: string; initials: string; bg: string };
  jobId: string;
}

const DEFAULT_BOARD_ITEMS: BoardCardItem[] = [
  // 1. To Verify (To Do)
  {
    id: "b-1",
    column: "to_do",
    tags: [
      { label: "Video", color: "purple" },
      { label: "Unprocessed", color: "yellow" },
    ],
    title: "Press Briefing Soundbite Alteration",
    description:
      "A 32-second clip circulating on Telegram claiming minister announced immediate currency re-denomination.",
    date: "29 Oct",
    commentsCount: 2,
    evidenceCount: 1,
    analyst: { name: "System Ingestion", initials: "SI", bg: "bg-[#E3DDF8] text-[#5D4EB4]" },
    jobId: "rep-audio-01",
  },
  {
    id: "b-2",
    column: "to_do",
    tags: [
      { label: "Audio", color: "purple" },
      { label: "WhatsApp Audio", color: "orange" },
    ],
    title: "Leaked Emergency Voice Note",
    description:
      "Forwarded voice note purportedly from municipal commissioner ordering power grid shutdown.",
    date: "29 Oct",
    commentsCount: 4,
    evidenceCount: 2,
    analyst: { name: "Wav2Vec2 Gate", initials: "W2", bg: "bg-[#FFE1CE] text-[#C05621]" },
    jobId: "rep-audio-01",
  },

  // 2. In Pipeline (In Progress)
  {
    id: "b-3",
    column: "in_progress",
    tags: [
      { label: "Video", color: "purple" },
      { label: "ASR & Stance", color: "sky" },
    ],
    title: "Parliamentary Budget Hearing Clip",
    description:
      "Extracting audio track for Wav2Vec2 vocoder analysis and querying Hansard transcript archives via Tavily.",
    date: "28 Oct",
    hasMediaPreview: true,
    mediaType: "video",
    anomalyScore: 0.94,
    commentsCount: 9,
    evidenceCount: 3,
    analyst: { name: "DeBERTa Judge", initials: "DB", bg: "bg-[#DDEFFC] text-[#0284C7]" },
    jobId: "rep-89241b",
  },
  {
    id: "b-4",
    column: "in_progress",
    tags: [
      { label: "Image", color: "yellow" },
      { label: "Spatial ResNet", color: "sky" },
    ],
    title: "Border Silo Construction Imagery",
    description:
      "ManTraNet quadrant scan for pixel copy-move splicing and ELA quantization consistency.",
    date: "28 Oct",
    commentsCount: 1,
    evidenceCount: 2,
    analyst: { name: "Smaug AI", initials: "SM", bg: "bg-[#E3DDF8] text-[#5D4EB4]" },
    jobId: "rep-38102a",
  },

  // 3. Flagged Synthetic (Under Review)
  {
    id: "b-5",
    column: "under_review",
    tags: [
      { label: "Speech Clone", color: "purple" },
      { label: "Disputed Claim", color: "orange" },
    ],
    title: "Viral Speech Video Manipulation",
    description:
      "Speech audio exhibits neural vocoder phase artifacts. Visual video matches 2024 footage but voiceover is AI generated.",
    date: "28 Oct",
    hasMediaPreview: true,
    mediaType: "video",
    anomalyScore: 0.94,
    commentsCount: 3,
    evidenceCount: 4,
    analyst: { name: "Kacie V.", initials: "KV", bg: "bg-[#FFE1CE] text-[#C05621]" },
    jobId: "rep-89241b",
  },
  {
    id: "b-6",
    column: "under_review",
    tags: [
      { label: "Image Splice", color: "orange" },
      { label: "Near-Match Reuse", color: "yellow" },
    ],
    title: "Grain Elevator Misrepresented as Missile Silo",
    description:
      "Pixel cloning localized in quadrants Q2/Q3. Historical pHash matches 2021 commercial grain storage facility.",
    date: "27 Oct",
    commentsCount: 3,
    evidenceCount: 3,
    analyst: { name: "Alia B.", initials: "AB", bg: "bg-[#D6F5EA] text-[#229E54]" },
    jobId: "rep-38102a",
  },

  // 4. Verified Clear (Ready)
  {
    id: "b-7",
    column: "ready",
    tags: [
      { label: "Audio", color: "mint" },
      { label: "Authentic Speech", color: "sky" },
    ],
    title: "Press Secretary Economic Briefing",
    description:
      "Continuous natural vocal tract resonance, uncompromised F0 pitch contour, and verified against government live feed.",
    date: "26 Oct",
    commentsCount: 0,
    evidenceCount: 5,
    analyst: { name: "Jeremy C.", initials: "JC", bg: "bg-[#DDEFFC] text-[#0284C7]" },
    jobId: "rep-clean-04",
  },
  {
    id: "b-8",
    column: "ready",
    tags: [
      { label: "Video", color: "mint" },
      { label: "Original Context", color: "sky" },
    ],
    title: "City Hall Public Address",
    description:
      "No spatial or temporal anomalies detected across all frames. Spoken claims corroborated by city hall transcripts.",
    date: "25 Oct",
    commentsCount: 1,
    evidenceCount: 6,
    analyst: { name: "Mya G.", initials: "MG", bg: "bg-[#D6F5EA] text-[#229E54]" },
    jobId: "rep-clean-04",
  },
];

interface KanbanBoardProps {
  items?: BoardCardItem[];
  searchQuery?: string;
  onOpenUpload?: () => void;
}

export function KanbanBoard({
  items = DEFAULT_BOARD_ITEMS,
  searchQuery = "",
  onOpenUpload,
}: KanbanBoardProps) {
  // Filter items by search query if provided
  const filteredItems = items.filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.tags.some((t) => t.label.toLowerCase().includes(q))
    );
  });

  const columns = [
    {
      id: "to_do",
      title: "To verify",
      count: filteredItems.filter((i) => i.column === "to_do").length,
    },
    {
      id: "in_progress",
      title: "In pipeline",
      count: filteredItems.filter((i) => i.column === "in_progress").length,
    },
    {
      id: "under_review",
      title: "Flagged synthetic",
      count: filteredItems.filter((i) => i.column === "under_review").length,
    },
    {
      id: "ready",
      title: "Verified clear",
      count: filteredItems.filter((i) => i.column === "ready").length,
    },
  ];

  const getTagColorClasses = (color: string) => {
    switch (color) {
      case "purple":
        return "bg-[#E3DAF8] text-[#553C9A]";
      case "orange":
        return "bg-[#FFE1CE] text-[#C05621]";
      case "yellow":
        return "bg-[#FDF0C6] text-[#B7791F]";
      case "mint":
        return "bg-[#D6F5EA] text-[#229E54]";
      case "sky":
      default:
        return "bg-[#B4DCFA] text-[#0284C7]";
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 select-none items-start">
      {columns.map((col) => {
        const colItems = filteredItems.filter((i) => i.column === col.id);

        return (
          <div key={col.id} className="flex flex-col gap-4">
            {/* Column Header matching mockup e.g. "To do (20)" */}
            <div className="flex items-center justify-between px-1">
              <h3 className="font-display font-bold text-[16px] text-[#111114]">
                {col.title}{" "}
                <span className="text-[#8E8E99] font-normal">({col.count})</span>
              </h3>
              {col.id === "to_do" && onOpenUpload && (
                <button
                  onClick={onOpenUpload}
                  className="text-[#8E8E99] hover:text-[#111114] text-[12px] font-semibold"
                >
                  + Add
                </button>
              )}
            </div>

            {/* Column Cards Container */}
            <div className="space-y-4">
              {colItems.map((item) => (
                <Link
                  key={item.id}
                  href={`/results/${item.jobId}`}
                  className="block bg-white rounded-[22px] p-5 border border-[#E8E3D7] shadow-xs hover:shadow-md transition-all duration-200 group relative"
                >
                  {/* Top Tags + 3-dots Menu */}
                  <div className="flex items-center justify-between mb-3.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      {item.tags.map((t, idx) => (
                        <span
                          key={idx}
                          className={`text-[12px] font-semibold px-2.5 py-1 rounded-[10px] ${getTagColorClasses(
                            t.color
                          )}`}
                        >
                          {t.label}
                        </span>
                      ))}
                    </div>

                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                      className="text-[#8E8E99] hover:text-[#111114] p-1 rounded-md hover:bg-[#F5F2EB] transition-colors"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Title */}
                  <h4 className="font-display font-bold text-[15.5px] text-[#111114] leading-snug group-hover:text-[#0284C7] transition-colors mb-2">
                    {item.title}
                  </h4>

                  {/* Description Snippet */}
                  <p className="text-[13px] text-[#6B6B75] leading-relaxed line-clamp-2 mb-4">
                    {item.description}
                  </p>

                  {/* Media Mockup Thumbnail (Just like the phone mockup in the image!) */}
                  {item.hasMediaPreview && (
                    <div className="mb-4 rounded-[16px] overflow-hidden bg-[#121316] p-3 border border-[#E4E4EA] text-white">
                      <div className="flex items-center justify-between text-[11px] font-mono text-white/60 mb-2">
                        <span className="flex items-center gap-1.5">
                          <Film className="w-3 h-3 text-[#7CC4F8]" />
                          Video Track Sensor
                        </span>
                        {item.anomalyScore && (
                          <span className="bg-[#E8667A] text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                            {(item.anomalyScore * 100).toFixed(0)}% Anomaly
                          </span>
                        )}
                      </div>

                      {/* Mini visual frame preview */}
                      <div className="relative h-24 rounded-[10px] bg-gradient-to-r from-[#1E2026] to-[#2B2D36] flex items-center justify-center overflow-hidden border border-white/10">
                        {/* Simulated audio waveform bars */}
                        <div className="flex items-end gap-1 h-10 opacity-70">
                          <div className="w-1.5 h-4 bg-[#7CC4F8] rounded-full" />
                          <div className="w-1.5 h-8 bg-[#E8667A] rounded-full animate-pulse" />
                          <div className="w-1.5 h-6 bg-[#E8667A] rounded-full" />
                          <div className="w-1.5 h-9 bg-[#E8667A] rounded-full" />
                          <div className="w-1.5 h-3 bg-[#7CC4F8] rounded-full" />
                          <div className="w-1.5 h-7 bg-[#E8667A] rounded-full" />
                          <div className="w-1.5 h-5 bg-[#7CC4F8] rounded-full" />
                        </div>

                        {/* Localized bounding indicator */}
                        <div className="absolute top-2 right-3 border border-dashed border-[#E8667A] text-[9px] font-mono px-1 py-0.5 text-[#E8667A] rounded">
                          Phase artifact
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Card Footer: Date + Assignee + Metrics */}
                  <div className="flex items-center justify-between pt-3 border-t border-[#F2EFE8] text-[12px] text-[#8E8E99]">
                    {/* Date Pill */}
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] border border-[#E8E3D7] text-[#6B6B75] font-medium text-[11.5px]">
                      <Calendar className="w-3.5 h-3.5 text-[#8E8E99]" />
                      <span>{item.date}</span>
                    </div>

                    {/* Right Cluster: Avatar + Comments + Paperclip */}
                    <div className="flex items-center gap-3">
                      {/* Avatar */}
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-[10px] ${item.analyst.bg}`}
                        title={item.analyst.name}
                      >
                        {item.analyst.initials}
                      </div>

                      {/* Comments */}
                      {item.commentsCount > 0 && (
                        <div className="flex items-center gap-1 font-mono text-[11.5px] text-[#6B6B75]">
                          <MessageSquare className="w-3.5 h-3.5 text-[#8E8E99]" />
                          <span>{item.commentsCount}</span>
                        </div>
                      )}

                      {/* Evidence / Attachments */}
                      {item.evidenceCount > 0 && (
                        <div className="flex items-center gap-1 font-mono text-[11.5px] text-[#6B6B75]">
                          <Paperclip className="w-3.5 h-3.5 text-[#8E8E99]" />
                          <span>{item.evidenceCount}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              ))}

              {colItems.length === 0 && (
                <div className="p-6 rounded-[20px] border-2 border-dashed border-[#E8E3D7] text-center text-[#8E8E99] text-sm">
                  No verifications in this state.
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
