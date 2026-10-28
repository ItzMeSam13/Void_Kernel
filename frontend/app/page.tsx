"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Upload, SlidersHorizontal, Filter } from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import PromoCard from "@/components/filters/PromoCard";
import FilterGroup from "@/components/filters/FilterGroup";
import ReportCard from "@/components/cards/ReportCard";
import Button from "@/components/ui/Button";
import { DEMO_REPORTS } from "@/lib/demo-data";

/**
 * Home page — Upload + recent checks (design 4.9).
 * Claim bar drives input. Drop zone + recent checks grid.
 */

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  const reports = DEMO_REPORTS;

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  }

  function handleSubmit() {
    // In production, this would call submitClaim() and route to results
    router.push(`/results/${DEMO_REPORTS[0].id}`);
  }

  return (
    <AppShell>
      <div className="px-5 md:px-8 lg:px-14 py-8 lg:py-12">
        {/* Mobile filter toggle */}
        <div className="lg:hidden mb-6">
          <Button
            variant="secondary"
            onClick={() => setFilterDrawerOpen(!filterDrawerOpen)}
          >
            <Filter size={16} strokeWidth={1.5} className="mr-2" />
            Filters
          </Button>
          {filterDrawerOpen && (
            <div className="mt-4 p-6 rounded-[20px]" style={{ background: "var(--card)", border: "1px solid var(--ink-200)" }}>
              <FilterGroup />
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-8 lg:gap-12">
          {/* ── Left column ────────────────────────── */}
          <aside className="hidden lg:flex flex-col gap-8">
            <PromoCard />
            <FilterGroup />
          </aside>

          {/* Vertical hairline (desktop only) */}

          {/* ── Main column ────────────────────────── */}
          <div>
            {/* Drop zone */}
            <div
              className={`rounded-[28px] p-8 mb-10 transition-all duration-200 cursor-pointer ${
                dragOver ? "scale-[1.01]" : ""
              }`}
              style={{
                background: "var(--pastel-sky)",
                border: dragOver
                  ? "1.5px dashed var(--ink-900)"
                  : "1.5px dashed rgba(14,14,16,0.3)",
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="flex flex-col items-center text-center py-8">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center mb-5"
                  style={{ background: "var(--card)" }}
                >
                  <Upload
                    size={28}
                    strokeWidth={1.5}
                    color="var(--ink-500)"
                  />
                </div>

                {selectedFile ? (
                  <>
                    <p
                      className="text-[17px] font-semibold mb-2"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      {selectedFile.name}
                    </p>
                    <p
                      className="text-[14px] font-medium mb-5"
                      style={{
                        color: "var(--ink-400)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                    <Button variant="accent" onClick={handleSubmit}>
                      Check this
                    </Button>
                  </>
                ) : (
                  <>
                    <p
                      className="text-[17px] font-medium mb-2"
                      style={{
                        color: "var(--text-on-light)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      Drop an image, video or voice note
                    </p>
                    <p
                      className="text-[14px] font-medium mb-5"
                      style={{
                        color: "var(--ink-400)",
                        fontFamily: "var(--font-inter), sans-serif",
                      }}
                    >
                      or click to browse · max 20 MB
                    </p>
                    <Button variant="accent">Choose file</Button>
                  </>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept="image/*,video/*,audio/*"
                  onChange={handleFileSelect}
                />
              </div>
            </div>

            {/* Section header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <h1
                  className="text-[40px] leading-[44px] font-extrabold tracking-[-0.02em]"
                  style={{
                    fontFamily: "var(--font-manrope), sans-serif",
                    color: "var(--text-on-light)",
                  }}
                >
                  Recent checks
                </h1>
                <span
                  className="px-5 py-1 rounded-full text-[22px] font-medium"
                  style={{
                    border: "1px solid var(--ink-200)",
                    color: "var(--text-on-light)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  {reports.length}
                </span>
              </div>

              <div className="hidden sm:flex items-center gap-2">
                <span
                  className="text-[14px] font-medium"
                  style={{
                    color: "var(--ink-400)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  Sort by:
                </span>
                <span
                  className="text-[14px] font-medium"
                  style={{
                    color: "var(--text-on-light)",
                    fontFamily: "var(--font-inter), sans-serif",
                  }}
                >
                  Last updated
                </span>
                <button
                  className="w-9 h-9 rounded-full flex items-center justify-center ml-1"
                  style={{ border: "1px solid var(--ink-200)" }}
                >
                  <SlidersHorizontal
                    size={14}
                    strokeWidth={1.5}
                    color="var(--ink-500)"
                  />
                </button>
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

            {/* Card grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {reports.map((report, i) => (
                <ReportCard key={report.id} report={report} index={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
