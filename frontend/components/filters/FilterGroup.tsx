"use client";

import React, { useState } from "react";
import { ChevronDown, RotateCcw } from "lucide-react";
import { CheckboxRow } from "./CheckboxRow";

export interface FilterState {
  modalities: string[];
  verdictStates: string[];
  evidenceFlags: string[];
}

interface FilterGroupProps {
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  onReset?: () => void;
}

export function FilterGroup({
  filters,
  onFilterChange,
  onReset,
}: FilterGroupProps) {
  const [collapsed, setCollapsed] = useState(false);

  const toggleModality = (val: string) => {
    const next = filters.modalities.includes(val)
      ? filters.modalities.filter((m) => m !== val)
      : [...filters.modalities, val];
    onFilterChange({ ...filters, modalities: next });
  };

  const toggleVerdict = (val: string) => {
    const next = filters.verdictStates.includes(val)
      ? filters.verdictStates.filter((v) => v !== val)
      : [...filters.verdictStates, val];
    onFilterChange({ ...filters, verdictStates: next });
  };

  const toggleEvidence = (val: string) => {
    const next = filters.evidenceFlags.includes(val)
      ? filters.evidenceFlags.filter((e) => e !== val)
      : [...filters.evidenceFlags, val];
    onFilterChange({ ...filters, evidenceFlags: next });
  };

  const hasActiveFilters =
    filters.modalities.length > 0 ||
    filters.verdictStates.length > 0 ||
    filters.evidenceFlags.length > 0;

  return (
    <div className="w-full flex flex-col select-none">
      {/* Filters Title Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[var(--ink-200)]">
        <h3 className="font-display font-bold text-[26px] text-[var(--text-on-light)] tracking-tight">
          Filters
        </h3>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={onReset}
              className="text-[13px] font-medium text-[var(--ink-400)] hover:text-[var(--text-on-light)] flex items-center gap-1 cursor-pointer transition-colors"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-7 h-7 rounded-full flex items-center justify-center text-[var(--ink-400)] hover:text-black hover:bg-[var(--ink-100)] transition-colors"
            aria-label="Toggle filters"
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform ${
                collapsed ? "-rotate-90" : ""
              }`}
            />
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="flex flex-col space-y-6 pt-5">
          {/* Group 1: Modality */}
          <div>
            <h4 className="text-[15px] font-medium text-[var(--ink-400)] mb-2.5">
              Modality
            </h4>
            <div className="flex flex-col">
              <CheckboxRow
                id="mod-video"
                label="Video"
                checked={filters.modalities.includes("video")}
                onChange={() => toggleModality("video")}
              />
              <CheckboxRow
                id="mod-image"
                label="Image"
                checked={filters.modalities.includes("image")}
                onChange={() => toggleModality("image")}
              />
              <CheckboxRow
                id="mod-audio"
                label="Audio"
                checked={filters.modalities.includes("audio")}
                onChange={() => toggleModality("audio")}
              />
              <CheckboxRow
                id="mod-text"
                label="Text only"
                checked={filters.modalities.includes("text")}
                onChange={() => toggleModality("text")}
              />
            </div>
          </div>

          {/* Group 2: Verdict State */}
          <div>
            <h4 className="text-[15px] font-medium text-[var(--ink-400)] mb-2.5">
              Verdict state
            </h4>
            <div className="flex flex-col">
              <CheckboxRow
                id="v-signal"
                label="Signal detected"
                checked={filters.verdictStates.includes("signal")}
                onChange={() => toggleVerdict("signal")}
              />
              <CheckboxRow
                id="v-clear"
                label="No strong signal"
                checked={filters.verdictStates.includes("clear")}
                onChange={() => toggleVerdict("clear")}
              />
              <CheckboxRow
                id="v-inconclusive"
                label="Inconclusive"
                checked={filters.verdictStates.includes("inconclusive")}
                onChange={() => toggleVerdict("inconclusive")}
              />
              <CheckboxRow
                id="v-na"
                label="Not assessed"
                checked={filters.verdictStates.includes("na")}
                onChange={() => toggleVerdict("na")}
              />
            </div>
          </div>

          {/* Group 3: Evidence */}
          <div>
            <h4 className="text-[15px] font-medium text-[var(--ink-400)] mb-2.5">
              Evidence flags
            </h4>
            <div className="flex flex-col">
              <CheckboxRow
                id="ev-source"
                label="Has source match"
                checked={filters.evidenceFlags.includes("source_match")}
                onChange={() => toggleEvidence("source_match")}
              />
              <CheckboxRow
                id="ev-echo"
                label="Echo-chamber warning"
                checked={filters.evidenceFlags.includes("echo_chamber")}
                onChange={() => toggleEvidence("echo_chamber")}
              />
              <CheckboxRow
                id="ev-recompress"
                label="Recompression caveat"
                checked={filters.evidenceFlags.includes("recompression")}
                onChange={() => toggleEvidence("recompression")}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

