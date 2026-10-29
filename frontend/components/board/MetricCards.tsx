"use client";

import React from "react";
import { Layers, Zap, CheckCircle2 } from "lucide-react";

export function MetricCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-5 select-none">
      {/* 1. Pastel Lavender Card */}
      <div className="bg-[#E2DAF8] rounded-[24px] p-6 flex flex-col justify-between min-h-[148px] shadow-xs hover:shadow-sm transition-shadow">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-[12px] bg-[#0E0E10] flex items-center justify-center text-white">
            <Layers className="w-4 h-4" />
          </div>
          <span className="font-semibold text-[15px] text-[#111114]">
            Total Verifications
          </span>
        </div>

        <div className="flex items-baseline gap-3 mt-4">
          <span className="text-[34px] font-display font-extrabold text-[#111114] tracking-tight">
            137
          </span>
          <span className="text-[13px] font-semibold text-[#111114]/80">
            +20% vs last month
          </span>
        </div>
      </div>

      {/* 2. Pastel Peach Card */}
      <div className="bg-[#FFBEA8] rounded-[24px] p-6 flex flex-col justify-between min-h-[148px] shadow-xs hover:shadow-sm transition-shadow">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-[12px] bg-[#0E0E10] flex items-center justify-center text-white">
            <Zap className="w-4 h-4 fill-white text-white" />
          </div>
          <span className="font-semibold text-[15px] text-[#111114]">
            Synthetic Detection Score
          </span>
        </div>

        <div className="flex items-baseline gap-3 mt-4">
          <span className="text-[34px] font-display font-extrabold text-[#111114] tracking-tight">
            8.6
          </span>
          <span className="text-[13px] font-semibold text-[#111114]/80">
            +0.5 vs last month
          </span>
        </div>
      </div>

      {/* 3. Pastel Sky Blue Card */}
      <div className="bg-[#B4DCFA] rounded-[24px] p-6 flex flex-col justify-between min-h-[148px] shadow-xs hover:shadow-sm transition-shadow">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-[12px] bg-[#0E0E10] flex items-center justify-center text-white">
            <CheckCircle2 className="w-4 h-4 stroke-[2.4]" />
          </div>
          <span className="font-semibold text-[15px] text-[#111114]">
            Corroboration Rate
          </span>
        </div>

        <div className="flex items-baseline gap-3 mt-4">
          <span className="text-[34px] font-display font-extrabold text-[#111114] tracking-tight">
            74%
          </span>
          <span className="text-[13px] font-semibold text-[#111114]/80">
            +10% vs last month
          </span>
        </div>
      </div>
    </div>
  );
}
