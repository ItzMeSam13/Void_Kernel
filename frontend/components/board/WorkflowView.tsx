"use client";

import React from "react";
import {
  Film,
  Mic,
  Search,
  CheckCircle2,
  Layers,
} from "lucide-react";

export function WorkflowView() {
  const steps = [
    {
      id: "ingest",
      title: "1. Media Ingestion & Splitting",
      subtitle: "FFmpeg & Librosa Decoders",
      desc: "Deconstructs container into synchronous raw 16kHz audio stream and keyframe image sequences.",
      icon: Film,
      bg: "bg-[#E3DAF8] text-[#553C9A]",
    },
    {
      id: "audio",
      title: "2. Audio Synthetic Forensics",
      subtitle: "mo-thecreator/Wav2Vec2 + Faster-Whisper",
      desc: "Scores phase vocoder distortion, F0 contour stability, and transcribes spoken claims to text.",
      icon: Mic,
      bg: "bg-[#FFE1CE] text-[#C05621]",
    },
    {
      id: "visual",
      title: "3. Spatial Anomaly Localization",
      subtitle: "Smaug-72B & ManTraNet ResNet50",
      desc: "Performs Error Level Analysis (ELA) and generates pixel-level splicing heatmaps.",
      icon: Layers,
      bg: "bg-[#FDF0C6] text-[#B7791F]",
    },
    {
      id: "fact",
      title: "4. Cross-Modal Grounding & NLI",
      subtitle: "OpenAI CLIP ViT-B/32 + Tavily + DeBERTa-v3",
      desc: "Retrieves independent news wire corroboration and evaluates directional entailment/contradiction.",
      icon: Search,
      bg: "bg-[#B4DCFA] text-[#0284C7]",
    },
  ];

  return (
    <div className="bg-white rounded-[24px] border border-[#E8E3D7] p-8 shadow-xs select-none">
      <div className="max-w-3xl mb-8">
        <h3 className="font-display font-bold text-[22px] text-[#111114] mb-2">
          Multi-Modal Forensic Orchestration Pipeline
        </h3>
        <p className="text-[14px] text-[#6B6B75] leading-relaxed">
          The pipeline evaluates claims across four independent verification axes. Early-exit gate conditions
          prevent hallucinated consensus, while tagged unions safeguard against fabricating unassessed scores.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 relative">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              className="p-5 rounded-[20px] bg-[#F9F7F2] border border-[#E8E3D7] flex flex-col justify-between min-h-[220px]"
            >
              <div>
                <div
                  className={`w-10 h-10 rounded-[14px] flex items-center justify-center font-bold mb-4 ${step.bg}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <h4 className="font-display font-bold text-[15.5px] text-[#111114] mb-1">
                  {step.title}
                </h4>
                <div className="text-[11.5px] font-mono text-[#0284C7] font-semibold mb-2">
                  {step.subtitle}
                </div>
                <p className="text-[12.5px] text-[#6B6B75] leading-relaxed">
                  {step.desc}
                </p>
              </div>

              <div className="pt-3 border-t border-[#E8E3D7] flex items-center justify-between text-[11px] font-mono text-[#8E8E99]">
                <span>Stage 0{idx + 1}</span>
                <span className="text-[#229E54] font-semibold">Active Ready</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Terminal Verdict Layer */}
      <div className="mt-6 p-5 rounded-[20px] bg-[#0E0E10] text-white flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-[14px] bg-[#229E54] flex items-center justify-center text-white">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <h5 className="font-display font-bold text-[15px]">
              Final 4-Axis Verdict & Natural Language Explanation
            </h5>
            <p className="text-[12px] text-white/70">
              Generates calibrated forensic reports with clickable superscript evidence citations without collapsing into a single fake/real score.
            </p>
          </div>
        </div>

        <div className="shrink-0">
          <span className="px-3 py-1.5 rounded-full bg-white/10 text-[12px] font-mono font-medium text-[#7CC4F8] border border-white/15">
            Architecture v1.0
          </span>
        </div>
      </div>
    </div>
  );
}