"use client";

import React, { useState } from "react";
import {
  Search,
  ArrowUpDown,
  Share2,
  Plus,
  List as ListIcon,
  X,
  Filter,
} from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { MetricCards } from "@/components/board/MetricCards";
import { KanbanBoard } from "@/components/board/KanbanBoard";
import { ListView } from "@/components/board/ListView";
import { NewVerificationModal } from "@/components/board/NewVerificationModal";

export default function HomePage() {
  const [view, setView] = useState<"board" | "list">("board");
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedModality, setSelectedModality] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"date" | "confidence">("date");

  return (
    <div className="bg-[#F5F1E8] min-h-screen p-4 sm:p-6 lg:p-8 flex flex-col lg:flex-row gap-6 max-w-[1780px] mx-auto antialiased">
      {/* 1. Left Floating Sidebar (Clarity style) */}
      <Sidebar
        activeTab="verifications"
        onOpenUpload={() => setIsUploadOpen(true)}
      />

      {/* 2. Main Investigation Dashboard Content */}
      <main className="flex-1 min-w-0 flex flex-col gap-6 select-none">
        {/* Top Header Row matching "Publications" in image */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
            <h1 className="font-display font-extrabold text-[28px] sm:text-[32px] text-[#111114] tracking-tight">
              Verifications
            </h1>

            {/* Segmented View Switcher: [ List ] [ 00 Board ] [ Workflow ] */}
            <div className="inline-flex items-center gap-1.5 p-1 rounded-full bg-transparent">
              {/* List Pill */}
              <button
                onClick={() => setView("list")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-[13px] font-semibold transition-all ${
                  view === "list"
                    ? "bg-[#0E0E10] text-white shadow-xs"
                    : "bg-white text-[#484852] border border-[#E8E3D7] hover:bg-[#FAF8F5]"
                }`}
              >
                <ListIcon className="w-3.5 h-3.5" />
                <span>List</span>
              </button>

              {/* Board Pill (default selected with 00 icon) */}
              <button
                onClick={() => setView("board")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-[13px] font-semibold transition-all ${
                  view === "board"
                    ? "bg-[#0E0E10] text-white shadow-xs"
                    : "bg-white text-[#484852] border border-[#E8E3D7] hover:bg-[#FAF8F5]"
                }`}
              >
                <span className="font-mono text-[12px] tracking-tighter">00</span>
                <span>Board</span>
              </button>
            </div>
          </div>

          {/* Right Action Buttons: [ + New Verification ] [ Share ] */}
          <div className="flex items-center gap-3 self-end sm:self-center">
            <button
              onClick={() => setIsUploadOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-[#0E0E10] text-white text-[13px] font-semibold hover:bg-black transition-colors shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>New Check</span>
            </button>

            <button
              onClick={() => {
                if (navigator.clipboard) {
                  navigator.clipboard.writeText(window.location.href);
                  alert("Link copied to clipboard!");
                }
              }}
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-[#E8E3D7] text-[#484852] text-[13px] font-semibold hover:bg-[#FAF8F5] transition-colors shadow-xs"
            >
              <Share2 className="w-4 h-4 text-[#8E8E99]" />
              <span>Share</span>
            </button>
          </div>
        </div>

        {/* Search and Filters Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Pill Search Field */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#8E8E99] absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search claims, transcripts, evidence..."
              className="w-full h-10 pl-11 pr-4 rounded-full bg-white border border-[#E8E3D7] text-[13.5px] text-[#111114] placeholder-[#8E8E99] focus:outline-none focus:ring-2 focus:ring-[#0284C7]/30 shadow-xs"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8E8E99] hover:text-[#111114]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Filter and Sort buttons */}
          <div className="flex items-center gap-2 self-end sm:self-center">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-[13px] font-semibold border transition-colors shadow-xs ${
                showFilters
                  ? "bg-[#0E0E10] text-white border-[#0E0E10]"
                  : "bg-white border-[#E8E3D7] text-[#484852] hover:bg-[#FAF8F5]"
              }`}
            >
              <Filter className="w-3.5 h-3.5 text-inherit" />
              <span>Filters</span>
            </button>

            <button
              onClick={() =>
                setSortBy(sortBy === "date" ? "confidence" : "date")
              }
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-[#E8E3D7] text-[#484852] text-[13px] font-semibold hover:bg-[#FAF8F5] transition-colors shadow-xs"
            >
              <ArrowUpDown className="w-3.5 h-3.5 text-[#8E8E99]" />
              <span>Sort by: {sortBy === "date" ? "Recent" : "Score"}</span>
            </button>
          </div>
        </div>

        {/* Expandable Filter Chips Bar */}
        {showFilters && (
          <div className="bg-white rounded-[20px] p-4 border border-[#E8E3D7] flex items-center gap-3 flex-wrap animate-in fade-in duration-150">
            <span className="text-[12px] font-semibold text-[#8E8E99]">
              Filter by Modality:
            </span>
            {["all", "video", "audio", "image"].map((mod) => (
              <button
                key={mod}
                onClick={() => setSelectedModality(mod)}
                className={`px-3 py-1 rounded-full text-[12px] font-semibold capitalize transition-colors ${
                  selectedModality === mod
                    ? "bg-[#0E0E10] text-white"
                    : "bg-[#F5F2EB] text-[#484852] hover:bg-[#EAE6DC]"
                }`}
              >
                {mod}
              </button>
            ))}
          </div>
        )}

        {/* 3 Pastel Metric Cards matching mockup */}
        <MetricCards />

        {/* Main Content Area based on View */}
        {view === "board" && (
          <KanbanBoard
            searchQuery={searchQuery}
            onOpenUpload={() => setIsUploadOpen(true)}
          />
        )}

        {view === "list" && (
          <ListView
            items={[
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
                commentsCount: 9,
                evidenceCount: 3,
                analyst: { name: "DeBERTa Judge", initials: "DB", bg: "bg-[#DDEFFC] text-[#0284C7]" },
                jobId: "rep-89241b",
              },
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
            ]}
          />
        )}
      </main>

      {/* Upload & Run Verification Modal */}
      <NewVerificationModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
      />
    </div>
  );
}