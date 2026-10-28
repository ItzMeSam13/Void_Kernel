"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import CheckboxRow from "./CheckboxRow";

/**
 * FilterGroup.tsx — The filters column (design 4.3).
 * Collapsible groups: Modality, Verdict state, Evidence.
 */

interface FilterState {
  modality: Record<string, boolean>;
  verdict: Record<string, boolean>;
  evidence: Record<string, boolean>;
}

export default function FilterGroup() {
  const [collapsed, setCollapsed] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    modality: {
      Image: false,
      Video: false,
      Audio: false,
      "Text only": false,
    },
    verdict: {
      "Signal detected": false,
      "No strong signal": false,
      Inconclusive: false,
      "Not assessed": false,
    },
    evidence: {
      "Has source match": false,
      "Echo-chamber warning": false,
      "Recompression caveat": false,
    },
  });

  function toggle(
    group: keyof FilterState,
    key: string,
    value: boolean
  ) {
    setFilters((prev) => ({
      ...prev,
      [group]: { ...prev[group], [key]: value },
    }));
  }

  const groups: {
    label: string;
    key: keyof FilterState;
    items: string[];
  }[] = [
    {
      label: "Modality",
      key: "modality",
      items: ["Image", "Video", "Audio", "Text only"],
    },
    {
      label: "Verdict state",
      key: "verdict",
      items: [
        "Signal detected",
        "No strong signal",
        "Inconclusive",
        "Not assessed",
      ],
    },
    {
      label: "Evidence",
      key: "evidence",
      items: [
        "Has source match",
        "Echo-chamber warning",
        "Recompression caveat",
      ],
    },
  ];

  return (
    <div>
      {/* Heading */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between w-full mb-4"
      >
        <h3
          className="text-[28px] font-bold"
          style={{
            fontFamily: "var(--font-manrope), sans-serif",
            color: "var(--text-on-light)",
          }}
        >
          Filters
        </h3>
        <ChevronDown
          size={18}
          strokeWidth={1.5}
          className={`transition-transform duration-200 ${
            collapsed ? "-rotate-90" : ""
          }`}
          color="var(--text-on-light)"
        />
      </button>

      {!collapsed && (
        <div className="space-y-1">
          {groups.map(({ label, key, items }) => (
            <div key={key}>
              <p
                className="text-[16px] font-medium mt-6 mb-2"
                style={{
                  color: "var(--ink-400)",
                  fontFamily: "var(--font-inter), sans-serif",
                }}
              >
                {label}
              </p>
              {items.map((item) => (
                <CheckboxRow
                  key={item}
                  label={item}
                  checked={filters[key][item]}
                  onChange={(v) => toggle(key, item, v)}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
