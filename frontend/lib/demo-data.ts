/* ──────────────────────────────────────────────────────────
   lib/demo-data.ts – Seed data for preview / demo mode
   Labeled "Demo data" in the UI per design rules.
   ────────────────────────────────────────────────────────── */

import type { Report, EvalData, SliceRow, ModuleMetrics } from "./types";

export const DEMO_REPORTS: Report[] = [
  {
    id: "RPT-20260520-001",
    claimText: "Massive flood engulfs residential area in City X overnight",
    mediaType: "image",
    mediaUrl: undefined,
    language: "Hindi",
    source: "Telegram",
    createdAt: "2026-05-20T14:32:00Z",
    bookmarked: false,
    axes: {
      claim_veracity: {
        status: "no_strong_signal",
        confidence: 0.78,
        tags: ["3 sources agree", "Verified news org"],
      },
      media_authenticity: {
        status: "inconclusive",
        confidence: 0.64,
        tags: ["Smaug 0.42", "ManTraNet clear", "Recompressed"],
        confidenceModifier: "recompression",
      },
      cross_modal_consistency: {
        status: "no_strong_signal",
        confidence: 0.81,
        tags: ["Caption matches scene", "OCR: Hindi"],
      },
      historical_reuse: {
        status: "signal_detected",
        confidence: 0.89,
        tags: ["Hamming d=3", "TinEye: 2019 match"],
      },
    },
    explanation:
      "Three independent sources corroborate the flooding event. However, media authenticity analysis could not reach a conclusion due to recompression artifacts. A reverse-image search found a visually similar image from 2019, raising a reuse signal.",
    evidenceItems: [
      {
        id: "ev-1",
        sourceDomain: "ndtv.com",
        date: "20 May, 2026",
        stance: "supports",
        snippet:
          "Heavy rains caused severe flooding in the residential districts of City X, displacing hundreds.",
        url: "https://example.com/ndtv-flood",
      },
      {
        id: "ev-2",
        sourceDomain: "altnews.in",
        date: "20 May, 2026",
        stance: "contradicts",
        snippet:
          "The image circulating is from a 2019 monsoon event in a different region, not the current flooding.",
        url: "https://example.com/altnews-check",
        isEchoChamber: false,
      },
      {
        id: "ev-3",
        sourceDomain: "whatsapp-forward.archive",
        date: "19 May, 2026",
        stance: "neutral",
        snippet:
          "Forwarded message with image and Hindi caption about flooding. No verifiable source attached.",
        url: "#",
        isEchoChamber: true,
      },
    ],
    biasRegulatorRan: true,
  },
  {
    id: "RPT-20260518-002",
    claimText:
      "Political leader promises free laptops to all students in state Y",
    mediaType: "video",
    mediaUrl: undefined,
    language: "English",
    source: "Twitter",
    createdAt: "2026-05-18T09:15:00Z",
    bookmarked: true,
    axes: {
      claim_veracity: {
        status: "signal_detected",
        confidence: 0.72,
        tags: ["No official statement found", "Misattributed quote"],
      },
      media_authenticity: {
        status: "no_strong_signal",
        confidence: 0.91,
        tags: ["No splicing detected", "Audio consistent"],
      },
      cross_modal_consistency: {
        status: "signal_detected",
        confidence: 0.55,
        tags: ["Subtitle mismatch", "Audio-visual sync OK"],
      },
      historical_reuse: {
        status: "not_assessed",
        reason: "Video too short for timeline analysis",
      },
    },
    explanation:
      "No official press release or government record supports this claim. The video itself appears unedited, but the subtitles do not match the spoken words accurately.",
    evidenceItems: [
      {
        id: "ev-4",
        sourceDomain: "pib.gov.in",
        date: "18 May, 2026",
        stance: "contradicts",
        snippet:
          "No announcement regarding free laptops was made by the state government in the referenced timeframe.",
        url: "https://example.com/pib-check",
      },
    ],
    biasRegulatorRan: false,
    videoTimeline: [
      { timestamp: 12, label: "Subtitle mismatch begins" },
      { timestamp: 34, label: "Suspicious audio transition" },
      { timestamp: 67, label: "Visual artifact detected" },
    ],
  },
  {
    id: "RPT-20260516-003",
    claimText:
      "Voice recording of official admitting corruption leaked on social media",
    mediaType: "audio",
    mediaUrl: undefined,
    language: "Marathi",
    source: "WhatsApp",
    createdAt: "2026-05-16T18:45:00Z",
    bookmarked: false,
    axes: {
      claim_veracity: {
        status: "inconclusive",
        confidence: 0.48,
        tags: ["Unverified identity", "No corroboration"],
      },
      media_authenticity: {
        status: "signal_detected",
        confidence: 0.73,
        tags: ["Splice point at 0:42", "Bitrate inconsistency"],
      },
      cross_modal_consistency: {
        status: "not_assessed",
        reason: "Audio-only submission, no visual component",
      },
      historical_reuse: {
        status: "no_strong_signal",
        confidence: 0.95,
        tags: ["No prior matches found"],
      },
    },
    explanation:
      "The audio shows signs of editing at the 42-second mark with a bitrate change. The speaker's identity cannot be confirmed from the recording alone, and no independent sources have verified the content of the alleged admission.",
    evidenceItems: [],
    biasRegulatorRan: true,
  },
  {
    id: "RPT-20260514-004",
    claimText: "New government scheme gives free ration to all BPL families",
    mediaType: "text",
    mediaUrl: undefined,
    language: "Hindi",
    source: "Facebook",
    createdAt: "2026-05-14T11:20:00Z",
    bookmarked: false,
    axes: {
      claim_veracity: {
        status: "no_strong_signal",
        confidence: 0.85,
        tags: ["Official gazette match", "PIB confirmation"],
      },
      media_authenticity: {
        status: "not_assessed",
        reason: "Text-only submission",
      },
      cross_modal_consistency: {
        status: "not_assessed",
        reason: "Text-only submission",
      },
      historical_reuse: {
        status: "no_strong_signal",
        confidence: 0.7,
        tags: ["Similar schemes documented since 2024"],
      },
    },
    explanation:
      "The claim aligns with an official government scheme announced in the gazette. The specific coverage ('all BPL families') matches the official scope.",
    evidenceItems: [
      {
        id: "ev-5",
        sourceDomain: "gazette.gov.in",
        date: "12 May, 2026",
        stance: "supports",
        snippet:
          "Government notification dated 10 May, 2026 extends free ration scheme to all Below Poverty Line households.",
        url: "https://example.com/gazette-ration",
      },
    ],
    biasRegulatorRan: false,
  },
  {
    id: "RPT-20260512-005",
    claimText:
      "Satellite image shows new military installations at the border",
    mediaType: "image",
    mediaUrl: undefined,
    language: "English",
    source: "Reddit",
    createdAt: "2026-05-12T07:00:00Z",
    bookmarked: true,
    axes: {
      claim_veracity: {
        status: "inconclusive",
        confidence: 0.41,
        tags: ["No official comment", "OSINT unverified"],
      },
      media_authenticity: {
        status: "inconclusive",
        confidence: 0.53,
        tags: ["Smaug 0.38", "Resolution too low"],
        confidenceModifier: "low resolution",
      },
      cross_modal_consistency: {
        status: "inconclusive",
        confidence: 0.5,
        tags: ["Geolocation uncertain"],
      },
      historical_reuse: {
        status: "no_strong_signal",
        confidence: 0.88,
        tags: ["No prior TinEye match"],
      },
    },
    explanation:
      "The image resolution is insufficient for reliable detector analysis. No official sources have commented on the claim, and open-source intelligence analysts have not verified the geolocation.",
    evidenceItems: [],
    biasRegulatorRan: true,
  },
  {
    id: "RPT-20260510-006",
    claimText:
      "Viral video shows earthquake in coastal town during festival",
    mediaType: "video",
    mediaUrl: undefined,
    language: "English",
    source: "Instagram",
    createdAt: "2026-05-10T20:10:00Z",
    bookmarked: false,
    axes: {
      claim_veracity: {
        status: "signal_detected",
        confidence: 0.82,
        tags: ["No seismic data match", "USGS: no event reported"],
      },
      media_authenticity: {
        status: "no_strong_signal",
        confidence: 0.87,
        tags: ["No edit detected", "Consistent metadata"],
      },
      cross_modal_consistency: {
        status: "signal_detected",
        confidence: 0.69,
        tags: ["Audio doesn't match visuals", "Dubbed audio detected"],
      },
      historical_reuse: {
        status: "signal_detected",
        confidence: 0.92,
        tags: ["Hamming d=1", "2024 earthquake footage"],
      },
    },
    explanation:
      "No seismic event was recorded by USGS or local authorities for the claimed date and location. The video appears to be authentic footage, but reverse-search matches it to a 2024 earthquake event in a different region. The audio track appears to have been added post-capture.",
    evidenceItems: [
      {
        id: "ev-6",
        sourceDomain: "earthquake.usgs.gov",
        date: "10 May, 2026",
        stance: "contradicts",
        snippet:
          "No seismic activity of magnitude ≥2.0 recorded in the claimed coastal region on the specified date.",
        url: "https://example.com/usgs",
      },
    ],
    biasRegulatorRan: true,
    videoTimeline: [
      { timestamp: 8, label: "Dubbed audio detected" },
      { timestamp: 45, label: "Frame duplication" },
      { timestamp: 72, label: "Audio doesn't match visual shaking" },
    ],
  },
];

/* ── Analytics demo data ─────────────────────────────────── */

const demoMetrics: ModuleMetrics[] = [
  {
    module: "Claim Veracity",
    precision: 0.84,
    recall: 0.79,
    fpr: 0.071,
    latencyP50: 1200,
    latencyP95: 3400,
    n: 140,
    ci95Low: 0.04,
    ci95High: 0.13,
  },
  {
    module: "Media Authenticity",
    precision: 0.91,
    recall: 0.82,
    fpr: 0.045,
    latencyP50: 2100,
    latencyP95: 5600,
    n: 210,
    ci95Low: 0.02,
    ci95High: 0.08,
  },
  {
    module: "Cross-modal Consistency",
    precision: 0.78,
    recall: 0.71,
    fpr: 0.11,
    latencyP50: 1800,
    latencyP95: 4200,
    n: 95,
    ci95Low: 0.06,
    ci95High: 0.19,
  },
  {
    module: "Historical Reuse",
    precision: 0.88,
    recall: 0.85,
    fpr: 0.032,
    latencyP50: 800,
    latencyP95: 2200,
    n: 180,
    ci95Low: 0.01,
    ci95High: 0.07,
  },
];

const demoSlices: SliceRow[] = [
  { dimension: "Language", value: "English", precision: 0.87, recall: 0.81, fpr: 0.05, n: 90 },
  { dimension: "Language", value: "Hindi", precision: 0.82, recall: 0.76, fpr: 0.08, n: 65 },
  { dimension: "Language", value: "Marathi", precision: 0.79, recall: 0.72, fpr: 0.1, n: 35 },
  { dimension: "Bitrate", value: "High (>4Mbps)", precision: 0.92, recall: 0.88, fpr: 0.03, n: 70 },
  { dimension: "Bitrate", value: "Low (<1Mbps)", precision: 0.74, recall: 0.68, fpr: 0.14, n: 45 },
  { dimension: "Compression", value: "Original", precision: 0.93, recall: 0.89, fpr: 0.02, n: 55 },
  { dimension: "Compression", value: "Recompressed", precision: 0.71, recall: 0.65, fpr: 0.16, n: 80 },
];

const demoRiskCoverage = [
  { risk: 0.0, coverage: 1.0 },
  { risk: 0.05, coverage: 0.92 },
  { risk: 0.1, coverage: 0.85 },
  { risk: 0.15, coverage: 0.78 },
  { risk: 0.2, coverage: 0.7 },
  { risk: 0.3, coverage: 0.58 },
  { risk: 0.4, coverage: 0.45 },
  { risk: 0.5, coverage: 0.32 },
  { risk: 0.6, coverage: 0.22 },
  { risk: 0.8, coverage: 0.1 },
  { risk: 1.0, coverage: 0.0 },
];

export const DEMO_EVAL_DATA: EvalData = {
  metrics: demoMetrics,
  slices: demoSlices,
  riskCoverage: demoRiskCoverage,
  isDemoData: true,
};
