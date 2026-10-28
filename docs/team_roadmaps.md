# Four-Person Roadmap

Splits `architecture.md`'s module map into four parallel tracks. The original three-role split
had one role ("Verifier") carrying roughly double the load of the other two — Module 6
(fact-checking) alone absorbed Veritas's entire pipeline plus the new entity-cross-check work, on
top of four other modules. That role is split in two here, along the natural seam in its own
responsibilities: a **verification pipeline** half and an **orchestration/platform** half.

- **Person 1A — Verification Pipeline.** Owns `multimodal_misinformation_module_guide.md`'s
  **Module C1–C3** (Tavily, Google Fact Check, NLI) plus the reuse sub-modules (**A6**, **B7**),
  and the architecture's new text/entity work (Module 2B, the entity cross-modal check). A
  self-contained subsystem: gather and judge evidence about a claim.
- **Person 1B — Orchestration, Fusion & Platform.** Owns the guide's **C4** (aggregation/
  explanation) reframed as per-axis fusion, plus the ingestion/orchestration skeleton and the
  API/Storage/Frontend layer that didn't come from either guide module — these are all
  system-wide-view responsibilities (the orchestrator needs to see every module's contract
  anyway), so they belong together.
- **Person 2 — Video Deepfake Engine** — owns `video_forensics_tech_spec.md` end to end, plus the
  guide's **B1/B6**. Unchanged from the three-person split — already a 1:1 mapping onto a single
  owner's brief.
- **Person 3 — Image + Audio Forensics** — owns the guide's **Module A** (A1–A5) and **B3–B5**.
  Also unchanged — both are per-asset synthetic-media classifiers, as opposed to Video's temporal
  multi-stream engine.

Each person's module(s) are built and tested standalone against the contract-first rule in
`architecture.md` §6 — no one needs another person's code to test their own module, only the
agreed Pydantic schema. Integration happens at the checkpoints marked below.

---

## Person 1A — Verification Pipeline

**Owns:** Module 2B `[new]`, Module 5, Module 6. Nothing here depends on the orchestrator, the
API, or the frontend — only on the other modules' output contracts (Module 5 is in fact one of
the earliest things *other* people depend on).

**Source material:**
- `multimodal_misinformation_module_guide.md` — Module C1 (Tavily), C2 (Google Fact Check), C3
  (NLI), A6 (historical image reuse), B7 (historical video reuse).
- `ml_exisitng_assets.md` — SHA-256+pHash (reuse as-is).
- `architecture.md` — every **[Improvement]** tagged under Module 5/6, plus Module 2B in full.

| Phase | Deliverable |
|---|---|
| 1 | Jointly with Person 1B: agree the `ClaimFindings` / `ReuseFindings` / `SyntheticTextFindings` output contracts — you author them, 1B consolidates them into `GraphState` |
| 1 | Module 5: hash/pHash lookup + `reference_media` table, ported from document_forgery — ship early, Persons 2 & 3 both call this |
| 1 | Module 6: claim splitter + adversarial Tavily search (skip drift guard/echo-chamber/NER for now) |
| 2 | **Module 2B `[new]`:** AI-generated-text classifier + length gate → `not_assessed` path — closes Deliverable 4's text gap |
| 3 | Module 6: drift guard, echo-chamber detection, **NER entity-tagging** on claims `[new]` |
| 3 | Module 5: widen contract to return `source_url`/`source_published_at`/`source_location`, not just a reuse flag `[new]` |
| 3 | Module 6: **entity × signal agreement matrix** — cross-check claim entities against Module 5's source metadata `[new]`, consume Person 3's widened-OCR scene-text output here too |
| 4 | **[new]** Module 2B perplexity-ratio cross-check (stretch); SerpApi reverse-image search if budget allows |
| 4 | Your slice of Module 8: claim-verification accuracy, explanation-quality scoring |

**Integration checkpoints you drive:** your three output contracts need to exist by end of
Phase 1 — 1B's orchestrator and fusion both consume them, and Module 5's lookup needs to exist
early since Persons 2 & 3 call it directly.

---

## Person 1B — Orchestration, Fusion & Platform

**Owns:** Module 1 (ingestion/orchestration skeleton), Module 7, Module 9 (API/Storage/
Frontend), and the LangGraph orchestration layer itself. This track is where every other
person's contract converges, so it's naturally the integration-lead role.

**Source material:**
- `multimodal_misinformation_module_guide.md` — C4 (final evidence aggregation and explanation).
- `ml_exisitng_assets.md` — Gemini semantic-validation pattern (reuse as-is).
- `architecture.md` — §6 (Modular Design & Orchestration Strategy) in full, Module 7's per-axis
  fusion redesign, Module 9's Supabase decision.

| Phase | Deliverable |
|---|---|
| 1 | `GraphState` schema — consolidates your own Module 1 needs plus the contracts Persons 1A, 2 & 3 each author for their own modules (contract-first, blocks everyone — do this *first*) |
| 1 | Module 7: rules-only fusion (no ML fusion yet), 4-axis output schema |
| 1 | Module 9: FastAPI `/analyze` + `/results` against a stub Supabase schema |
| 2 | Module 1: ARQ queue + SHA-256 7-day cache |
| 2 | Supabase schema finalized: `jobs`, `module_findings`, `reference_media`, `evidence_sources`; Storage buckets for heatmaps |
| 3 | Module 7: per-axis weighted fusion, evidence-grounded explanation prompt (Gemini) — consume Person 2's `spectral_artifact_score` and `signal_integrity_score` as two separate inputs (one axis evidence, one confidence modifier), not one merged field |
| 3 | **Orchestration build-out:** stand up the LangGraph `StateGraph`, starting with Module 1's router wired to one stub branch (per §6's build sequence), then swap in Persons 1A/2/3's real modules as each stabilizes. Note the scope boundary: *this* top-level graph is yours; Module 6's internal per-claim `Send` fan-out (Veritas's pattern) is implemented inside Person 1A's module, not here |
| 4 | Eval harness (Module 8) integration — surface all four people's eval slices in the analytics view |
| 4 | Lead the full four-way integration test with real sample media |

**Integration checkpoints you drive:** freeze every other module's output contract by end of
Phase 1 (you need all of them to build `GraphState`, the orchestrator, and fusion), and own the
final `StateGraph` wiring.

---

## Person 2 — Video Deepfake Engine

**Owns:** Module 3, entirely. This is the one module whose spec is already written at
implementation detail — follow `video_forensics_tech_spec.md` directly.

**Source material:**
- `video_forensics_tech_spec.md` — all of it: Stage 1–4 pipeline, Task 1–3 (spectral/spatial/
  rPPG), the JSON contract in §4, and your part of §5's integration workflow (named there as the
  **"Video Module Owner"**, covering Deliverable 6's "unseen manipulation" requirement).
- `ml_exisitng_assets.md` — "video deepfake detector... zero video capability exists anywhere in
  the codebase" (missing, build-from-scratch list) — this gap is your entire job.

| Phase | Deliverable |
|---|---|
| 1 | Nothing blocking — can start immediately once `GraphState` contracts land from Person 1B. Build Stage 1: `cv2.VideoCapture` dense snippet extraction (three 30-frame windows at 10/50/90%) |
| 1 | Stage 2: MediaPipe FaceMesh, 468 landmarks, 15% bbox padding |
| 2 | Task 1 (Spectral), **with a fix on top of the spec as written `[fix]`:** compute the 2D-DCT, then split corner energy into two sub-features instead of one — periodic/checkerboard energy → `spectral_artifact_score` (AI-generation evidence, Deliverable 4), broadband/non-periodic energy → `signal_integrity_score` (recompression/perturbation evidence, Deliverable 6). Without this split, an ordinary reposted/re-encoded real video reads as "AI-generated" — see `architecture.md` Module 3 for the full rationale. Add `confounded_by_recompression: true` → `inconclusive` when `signal_integrity_score` is high, rather than asserting both at once |
| 2 | Task 3 (rPPG): forehead green-channel bandpass (0.7–2.5 Hz) + FFT peak check |
| 2 | Wire Person 3's `analyze_image()` contract onto your sampled frames (BLIP/CLIP/OCR/Smaug per frame) — call it as a black box, don't reimplement any of it |
| 3 | Task 2 (Spatial): ViT (`SiglipForImageClassification`) + attention rollout, intersected with MediaPipe landmarks → the human-readable localization string (most complex stream, needs a labeled deepfake set — FaceForensics++/DFDC — to validate thresholds) |
| 3 | Stage 4: weighted-peak fusion of the three streams → the JSON contract exactly as specified in §4 (`verdict`, `confidence_score`, `forensic_streams`, `flagged_segments_sec`, `concrete_evidence[]`, `saliency_heatmap_path`) |
| 3 | Call Person 1A's Module 5 reuse-lookup on your extracted keyframes for historical-video-reuse coverage (guide's B7) — again, black-box call, not your model to own |
| 4 | (Stretch, joint with Person 3) SyncNet A/V sync cross-check against Person 3's lip-sync timestamps |
| 4 | Your slice of Module 8: accuracy/FPR on a labeled deepfake-video set, robustness pass (re-encode at 2 bitrates, crop/rescale, re-run, diff verdicts) |

**Keep the boundary explicit per `architecture.md`'s [Improvement] note:** your `verdict` answers
"was this synthetically generated," never "has this been seen before" — that's Person 1A's
Module 5, called, not merged into your output. Keep a second boundary explicit too:
`spectral_artifact_score` (generation evidence) and `signal_integrity_score` (recompression/
perturbation evidence) are two different claims from the same DCT output — don't let one imply
the other.

**Integration checkpoints:** freeze your JSON output contract early (Phase 1–2) since Person 1B's
Module 7 consumes `concrete_evidence[]` directly for explanation generation.

---

## Person 3 — Image + Audio Deepfake / Forensics

**Owns:** Module 2, entirely, and Module 4, entirely.

**Source material:**
- `multimodal_misinformation_module_guide.md` — Module A (A1 BLIP caption, A2 CLIP similarity,
  A3 PaddleOCR, A4 Smaug AI-image detector, A5 manipulation localization), B3–B5 (audio
  extraction, Whisper transcription, Wav2Vec2/AASIST deepfake-audio detection).
- `video_forensics_tech_spec.md` §5 — your audio half of cross-modal sync is named there as the
  **"Audio Team"** (phoneme-to-viseme lip-sync timestamps, compared against Person 2's
  `flagged_segments_sec`).
- `ml_exisitng_assets.md` — ManTraNet/BusterNet (**reuse as-is**, `document_forgery/app/backend/imageforensic/member2_spatial_forensics.py`); Swin-Transformer / EfficientNet-B0 backbones
  (needs-fine-tuning list, stretch only); Wav2Vec2 deepfake-audio (`mo-thecreator/Deepfake-audio-detection`, reuse as-is per the guide's recommendation).

| Phase | Deliverable |
|---|---|
| 1 | Port `member2_spatial_forensics.py` out of document_forgery, validate it still separates tampered/clean on ~50 labeled *natural* (non-document) images |
| 1 | Wrap BLIP + CLIP + PaddleOCR as plain Python functions (no LangChain adapters) |
| 1 | Integrate Smaug AI-image detector |
| 1 | Single `analyze_image(image, claim_text) -> ImageFindings` entrypoint — freeze this contract early, Person 2 calls it per-frame |
| 2 | **[new]** Widen PaddleOCR's scope beyond embedded caption text to incidental background text (street signs, storefronts, banners) — one extra field on your existing output contract, feeds Person 1A's entity cross-check directly |
| 2 | FFmpeg audio extraction → mono 16kHz WAV |
| 2 | Whisper `small`/faster-whisper transcription → claim text handed to Person 1A's Module 6 |
| 3 | Wav2Vec2 deepfake-audio scorer, output labeled `synthetic_audio_signal_detected` / `no_strong_signal_detected` / `inconclusive` — never a binary real/fake claim |
| 3 | (Stretch) AASIST as an alternative audio detector, only if time + labeled data allow |
| 4 | (Stretch, joint with Person 2) SyncNet A/V sync — your lip-sync phoneme-to-viseme side, cross-checked against Person 2's flagged timestamps |
| 4 | (Stretch) Retrain Swin/EfficientNet-B0 backbones as a natural-image manipulation head / lightweight GAN-artifact classifier, replacing the document-specific heads |
| 4 | Your slice of Module 8: accuracy on natural-image manipulation (ManTraNet) and AI-image detection (Smaug), synthetic-audio detection accuracy, robustness pass |

**Integration checkpoints:** your `ImageFindings` contract (Phase 1) is the single highest-priority
freeze in the whole project — Person 2 (per-frame calls) and Person 1B (fusion input) both depend
on it before they can integrate anything.

---

## Cross-Team Dependency Map

| Producer | Output | Consumer |
|---|---|---|
| Person 1A (Module 5) | hash/pHash reuse lookup + structured source metadata | Person 2 (video keyframes), Person 3 (images) |
| Person 1A (Module 6) | `ClaimFindings` | Person 1B (Module 7, fusion input) |
| Person 1A (Module 2B) | `SyntheticTextFindings` | Person 1B (Module 7, fusion input) |
| Person 3 (Module 2) | `analyze_image()` — caption/CLIP/OCR/Smaug/manipulation | Person 2 (per-frame, inside Module 3) |
| Person 3 (Module 2, widened OCR) | background/scene text | Person 1A (Module 6 entity cross-check) `[new wiring]` |
| Person 3 (Module 4) | Whisper transcript | Person 1A (Module 6, claim source for video) |
| Person 2 (Module 3) | `flagged_segments_sec`, `concrete_evidence[]`, split spectral scores | Person 1B (Module 7, explanation input); Person 3 (optional SyncNet cross-check) |
| Person 1B (Module 1) | `GraphState` + consolidated contract schema | Everyone — must land first, Phase 1 |

## Integration Sequence (all four together)

1. **End of Phase 1:** all four people's output contracts (`ImageFindings`, the video module's
   JSON schema, `ClaimFindings`/`ReuseFindings`/`SyntheticTextFindings`, `GraphState`) are
   frozen, even if the models behind them are stubs returning dummy data.
2. **Early Phase 2:** Person 1B stands up the thinnest LangGraph `StateGraph` — router → one stub
   branch — per `architecture.md` §6, so the wiring is validated before every module is finished.
3. **Through Phase 3:** each person's real module swaps in for its stub node as it stabilizes.
   No orchestration code changes when this happens — that's the point of the contract boundary.
   This happens on a rolling basis, not synchronized to a shared calendar date — Person 3's
   Module 2 may well be ready to swap in before Person 2's tri-stream engine is.
4. **Phase 4:** full four-way integration test with real (not simulated) sample media, then each
   person's slice of Module 8 runs against labeled data for final accuracy/robustness numbers.
