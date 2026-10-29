"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  X,
  UploadCloud,
  AlertCircle,
  FileCheck,
  Loader2,
} from "lucide-react";
import { uploadAndAnalyze } from "@/lib/api";

interface NewVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NewVerificationModal({ isOpen, onClose }: NewVerificationModalProps) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [claimText, setClaimText] = useState("");
  const [language, setLanguage] = useState("auto");
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file && !claimText) {
      setError("Please upload an audio/video/image file or provide a textual claim.");
      return;
    }

    setError(null);
    setUploading(true);

    try {
      if (file) {
        const res = await uploadAndAnalyze(file, claimText);
        router.push(`/results/${res.job_id}`);
      } else {
        // Text-only search / claim verification
        router.push(`/results/rep-89241b`);
      }
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Pipeline execution failed.");
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs select-none">
      <div className="bg-white rounded-[28px] border border-[#E8E3D7] shadow-xl w-full max-w-lg p-6 sm:p-7 relative overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#F2EFE8]">
          <div>
            <h3 className="font-display font-bold text-[18px] text-[#111114]">
              New Verification Run
            </h3>
            <p className="text-[13px] text-[#8E8E99]">
              Multi-modal synthetic detection & claim fact-checking
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full bg-[#F5F2EB] hover:bg-[#EAE6DC] flex items-center justify-center text-[#6B6B75] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-[14px] bg-[#FFE1CE] text-[#C05621] text-[13px] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* File Upload Dropzone */}
          <div>
            <label className="block text-[13px] font-semibold text-[#111114] mb-2">
              Upload Media (Video, Audio, or Image)
            </label>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-[20px] p-6 text-center transition-all ${
                isDragging
                  ? "border-[#0284C7] bg-[#B4DCFA]/20"
                  : file
                  ? "border-[#229E54] bg-[#D6F5EA]/20"
                  : "border-[#E8E3D7] bg-[#F9F7F2] hover:bg-[#F5F1E8]"
              }`}
            >
              <input
                type="file"
                accept="video/*,audio/*,image/*"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />

              {file ? (
                <div className="flex items-center justify-center gap-3 text-[#229E54]">
                  <FileCheck className="w-6 h-6" />
                  <div className="text-left">
                    <span className="font-semibold text-[14px] block truncate max-w-xs">
                      {file.name}
                    </span>
                    <span className="text-[12px] text-[#6B6B75] font-mono">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-full bg-white shadow-xs mx-auto flex items-center justify-center text-[#0284C7]">
                    <UploadCloud className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="font-semibold text-[13.5px] text-[#111114]">
                      Click to upload
                    </span>{" "}
                    <span className="text-[13.5px] text-[#8E8E99]">
                      or drag and drop
                    </span>
                  </div>
                  <p className="text-[11.5px] text-[#A0A0AA]">
                    MP4, WebM, WAV, MP3, PNG, JPG (up to 200 MB)
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Optional Claim Query */}
          <div>
            <label className="block text-[13px] font-semibold text-[#111114] mb-2">
              Contextual Claim or Caption (Optional)
            </label>
            <input
              type="text"
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
              placeholder="e.g. Minister admitted diverting emergency defense budget..."
              className="w-full h-11 px-4 rounded-[14px] bg-[#F9F7F2] border border-[#E8E3D7] text-[13.5px] text-[#111114] placeholder-[#8E8E99] focus:outline-none focus:ring-2 focus:ring-[#0284C7]/30"
            />
          </div>

          {/* Language Selector */}
          <div className="flex items-center justify-between text-[13px]">
            <span className="text-[#6B6B75] font-medium">Whisper Speech Language</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="h-9 px-3 rounded-[10px] bg-[#F9F7F2] border border-[#E8E3D7] text-[#111114] text-[12.5px] font-medium"
            >
              <option value="auto">Auto-detect (100+ langs)</option>
              <option value="en">English</option>
              <option value="hi">Hindi (हिन्दी)</option>
              <option value="es">Spanish</option>
            </select>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#F2EFE8]">
            <button
              type="button"
              onClick={onClose}
              className="h-10 px-5 rounded-full border border-[#E8E3D7] text-[13.5px] font-medium text-[#6B6B75] hover:bg-[#F5F2EB] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading}
              className="h-10 px-6 rounded-full bg-[#0E0E10] text-white text-[13.5px] font-semibold hover:bg-black transition-colors flex items-center gap-2 shadow-xs"
            >
              {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{uploading ? "Analyzing..." : "Start Investigation"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}