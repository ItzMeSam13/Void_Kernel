/* ──────────────────────────────────────────────────────────
   lib/api.ts – Typed client for /api/v1/*
   All API calls go through here so components stay clean.
   ────────────────────────────────────────────────────────── */

import type {
  Report,
  ReportsListResponse,
  JobSubmitResponse,
  EvalData,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/* ── Reports ────────────────────────────────────────────── */

export async function getReports(params?: {
  modality?: string;
  verdict?: string;
  sort?: string;
  confMin?: number;
  confMax?: number;
}): Promise<ReportsListResponse> {
  const qs = new URLSearchParams();
  if (params?.modality) qs.set("modality", params.modality);
  if (params?.verdict) qs.set("verdict", params.verdict);
  if (params?.sort) qs.set("sort", params.sort);
  if (params?.confMin !== undefined) qs.set("conf_min", String(params.confMin));
  if (params?.confMax !== undefined) qs.set("conf_max", String(params.confMax));
  const q = qs.toString();
  return request<ReportsListResponse>(`/reports${q ? `?${q}` : ""}`);
}

export async function getReport(id: string): Promise<Report> {
  return request<Report>(`/results/${id}`);
}

export async function submitClaim(data: {
  claimText: string;
  mediaType: string;
  language: string;
  file?: File;
}): Promise<JobSubmitResponse> {
  const formData = new FormData();
  formData.set("claim_text", data.claimText);
  formData.set("media_type", data.mediaType);
  formData.set("language", data.language);
  if (data.file) formData.set("file", data.file);

  const res = await fetch(`${API_BASE}/check`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json() as Promise<JobSubmitResponse>;
}

export async function pollResults(jobId: string): Promise<Report> {
  return request<Report>(`/results/${jobId}`);
}

/* ── Analytics / eval ───────────────────────────────────── */

export async function getEvalData(module?: string): Promise<EvalData> {
  const path = module ? `/eval/${module}` : "/eval";
  return request<EvalData>(path);
}
