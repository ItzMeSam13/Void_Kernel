"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { BoardCardItem } from "./KanbanBoard";

interface ListViewProps {
  items: BoardCardItem[];
}

export function ListView({ items }: ListViewProps) {
  return (
    <div className="bg-white rounded-[24px] border border-[#E8E3D7] overflow-hidden shadow-xs select-none">
      <div className="divide-y divide-[#F2EFE8]">
        {items.map((item) => (
          <Link
            key={item.id}
            href={`/results/${item.jobId}`}
            className="flex flex-col sm:flex-row sm:items-center justify-between p-5 hover:bg-[#F9F7F2] transition-colors gap-4 group"
          >
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                {item.tags.map((t, idx) => (
                  <span
                    key={idx}
                    className="text-[11.5px] font-semibold px-2.5 py-0.5 rounded-[8px] bg-[#F5F2EB] text-[#484852]"
                  >
                    {t.label}
                  </span>
                ))}
                <span className="text-[12px] font-mono text-[#8E8E99]">
                  • {item.date}
                </span>
              </div>

              <h4 className="font-display font-bold text-[16px] text-[#111114] group-hover:text-[#0284C7] transition-colors truncate">
                {item.title}
              </h4>

              <p className="text-[13px] text-[#6B6B75] truncate max-w-2xl">
                {item.description}
              </p>
            </div>

            <div className="flex items-center gap-6 shrink-0 self-end sm:self-center">
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-[11px] ${item.analyst.bg}`}
                >
                  {item.analyst.initials}
                </div>
                <span className="text-[12px] font-medium text-[#6B6B75] hidden md:inline">
                  {item.analyst.name}
                </span>
              </div>

              <div className="flex items-center gap-1.5 text-[13px] font-semibold text-[#111114]">
                <span>Inspect</span>
                <ArrowRight className="w-4 h-4 text-[#8E8E99] group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
