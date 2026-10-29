"use client";

import React, { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  Activity,
  CheckSquare,
  MessageSquare,
  Settings,
  Plus,
  Film,
  Mic,
  Layers,
  ShieldCheck,
  LogOut,
  Shield,
} from "lucide-react";

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  onOpenUpload?: () => void;
}

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: LayoutGrid, href: "/" },
  { id: "activity", label: "Activity", icon: Activity, href: "/analytics" },
  { id: "verifications", label: "Verifications", icon: CheckSquare, href: "/" },
  { id: "chat", label: "Evidence Chat", icon: MessageSquare, href: "#chat" },
  { id: "settings", label: "Settings", icon: Settings, href: "#settings" },
];

function SidebarNavItems({
  activeTab,
  onSelectTab,
}: {
  activeTab: string;
  onSelectTab?: (tab: string) => void;
}) {
  const pathname = usePathname();

  return (
    <nav className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isPathActive =
          item.id === "activity"
            ? pathname === "/analytics"
            : item.id === "verifications" || item.id === "overview"
            ? pathname === "/"
            : false;
        const isTabActive = activeTab === item.id || isPathActive;

        return (
          <Link
            key={item.id}
            href={item.href}
            onClick={() => onSelectTab && onSelectTab(item.id)}
            className={`flex items-center gap-3.5 px-3.5 py-2.5 rounded-[16px] text-[14.5px] font-medium transition-all duration-150 ${
              isTabActive
                ? "bg-[#F5F2EB] text-[#111114] font-semibold"
                : "text-[#6B6B75] hover:text-[#111114] hover:bg-[#F9F7F2]"
            }`}
          >
            <Icon
              className={`w-4.5 h-4.5 ${
                isTabActive ? "text-[#111114]" : "text-[#8E8E99]"
              }`}
            />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarNavFallback({
  activeTab,
  onSelectTab,
}: {
  activeTab: string;
  onSelectTab?: (tab: string) => void;
}) {
  return (
    <nav className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isTabActive = activeTab === item.id;

        return (
          <Link
            key={item.id}
            href={item.href}
            onClick={() => onSelectTab && onSelectTab(item.id)}
            className={`flex items-center gap-3.5 px-3.5 py-2.5 rounded-[16px] text-[14.5px] font-medium transition-all duration-150 ${
              isTabActive
                ? "bg-[#F5F2EB] text-[#111114] font-semibold"
                : "text-[#6B6B75] hover:text-[#111114] hover:bg-[#F9F7F2]"
            }`}
          >
            <Icon
              className={`w-4.5 h-4.5 ${
                isTabActive ? "text-[#111114]" : "text-[#8E8E99]"
              }`}
            />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ activeTab = "verifications", onSelectTab, onOpenUpload }: SidebarProps) {
  const pipelines = [
    { name: "Video Forensics", icon: Film, count: "12 runs" },
    { name: "Audio Deepfake", icon: Mic, count: "28 runs" },
    { name: "Cross-Modal CLIP", icon: Layers, count: "19 runs" },
    { name: "Fact-Checking NLI", icon: ShieldCheck, count: "45 runs" },
  ];

  const evaluators = [
    {
      name: "mo-thecreator",
      role: "Wav2Vec2 Classifier",
      metric: "98.4% audio acc",
      avatarBg: "bg-[#FFE1CE] text-[#C05621]",
      initials: "W2",
    },
    {
      name: "Faster-Whisper",
      role: "CTranslate2 ASR",
      metric: "0.2s latency",
      avatarBg: "bg-[#D6F5EA] text-[#229E54]",
      initials: "FW",
    },
    {
      name: "DeBERTa-v3",
      role: "Stance Judge NLI",
      metric: "91.2% F1 score",
      avatarBg: "bg-[#DDEFFC] text-[#0284C7]",
      initials: "DB",
    },
    {
      name: "Smaug-72B",
      role: "Spatial Anomaly",
      metric: "0.91 AUC-ROC",
      avatarBg: "bg-[#E3DDF8] text-[#5D4EB4]",
      initials: "SM",
    },
  ];

  return (
    <aside className="w-full lg:w-[260px] xl:w-[280px] bg-white rounded-[28px] border border-[#E8E3D7] p-5 lg:p-6 flex flex-col justify-between shadow-xs shrink-0 select-none">
      <div className="space-y-7">
        {/* Brand / Logo matching "Clarity" in mockup */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-[12px] bg-[#0E0E10] flex items-center justify-center text-white shadow-xs group-hover:scale-105 transition-transform">
            <Shield className="w-5 h-5 fill-current" />
          </div>
          <span className="font-display font-extrabold text-[24px] text-[#111114] tracking-[-0.03em]">
            Nith
          </span>
        </Link>

        {/* Primary Navigation with Suspense wrapper */}
        <Suspense fallback={<SidebarNavFallback activeTab={activeTab} onSelectTab={onSelectTab} />}>
          <SidebarNavItems activeTab={activeTab} onSelectTab={onSelectTab} />
        </Suspense>

        {/* Pipelines / Projects Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-[13px] font-semibold text-[#8E8E99]">Pipelines</span>
            <button
              onClick={onOpenUpload}
              className="text-[#8E8E99] hover:text-[#111114] p-0.5 rounded hover:bg-[#F5F2EB] transition-colors"
              title="Add pipeline run"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1">
            {pipelines.map((pipe) => {
              const Icon = pipe.icon;
              return (
                <div
                  key={pipe.name}
                  onClick={onOpenUpload}
                  className="flex items-center justify-between px-3 py-2 rounded-[14px] text-[13.5px] font-medium text-[#484852] hover:bg-[#F9F7F2] hover:text-[#111114] transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-3 truncate">
                    <Icon className="w-4 h-4 text-[#8E8E99] group-hover:text-[#111114]" />
                    <span className="truncate">{pipe.name}</span>
                  </div>
                  <span className="text-[11px] font-mono text-[#A0A0AA] group-hover:text-[#6B6B75]">
                    {pipe.count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Members / Active Evaluators Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-[13px] font-semibold text-[#8E8E99]">Active Models</span>
            <button
              onClick={onOpenUpload}
              className="text-[#8E8E99] hover:text-[#111114] p-0.5 rounded hover:bg-[#F5F2EB] transition-colors"
              title="Manage models"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-2">
            {evaluators.map((ev) => (
              <div
                key={ev.name}
                className="flex items-center gap-3 px-2 py-1.5 rounded-[14px] hover:bg-[#F9F7F2] transition-colors cursor-pointer"
              >
                <div className="relative">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[11px] ${ev.avatarBg}`}
                  >
                    {ev.initials}
                  </div>
                  <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-[#22C55E] rounded-full ring-2 ring-white" />
                </div>
                <div className="leading-tight truncate">
                  <div className="font-semibold text-[13px] text-[#111114] truncate">
                    {ev.name}
                  </div>
                  <div className="text-[11px] text-[#8E8E99] truncate font-mono">
                    {ev.metric}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Footer: Log out / API Docs */}
      <div className="pt-6 border-t border-[#EFECE3] mt-6">
        <Link
          href="https://github.com"
          target="_blank"
          className="flex items-center gap-3 px-3 py-2 rounded-[14px] text-[13.5px] font-medium text-[#6B6B75] hover:text-[#111114] hover:bg-[#F5F2EB] transition-colors"
        >
          <LogOut className="w-4.5 h-4.5 text-[#8E8E99]" />
          <span>Documentation</span>
        </Link>
      </div>
    </aside>
  );
}
