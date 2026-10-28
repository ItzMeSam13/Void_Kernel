# PS-2 Multimodal Misinformation Detection — Final Architecture

This is the integrated architecture for the project, merging the three planning docs in this
folder (`multimodal_misinformation_module_guide.md`, `video_forensics_tech_spec.md`,
`ml_exisitng_assets.md`) into one coherent module map, plus patterns worth importing from the
two reference repos:

- **`document_forgery`** — a document-forensics system with a working fusion engine,
  blockchain/hash provenance layer, and a Celery-based async pipeline. Its generic
  (non-document-specific) model weights and infra patterns are reusable here.
- **`Veritas` (Odis)** — a text/claim fact-checking platform built on LangGraph, with safety
  mechanisms (echo-chamber detection, essence-drift guard, adversarial search, result caching)
  that the module guide's fact-checking module (Module C) does not yet have, but should.

Nothing below is a from-scratch redesign — it is the three docs reconciled into one pipeline,
with every reuse opportunity and every gap called out explicitly, plus the improvements noted
inline as **[Improvement]**.

---

## 1. Guiding Principles

Carried over from `multimodal_misinformation_module_guide.md` §6, and extended with
Veritas's and document_forgery's safety mechanisms:

1. **Separate findings, never collapse them.** Claim veracity, media authenticity (AI-generated
   / manipulated), cross-modal consistency, and historical reuse are four independent axes.
   Never let one stand in for another.
2. **Signals, not verdicts.** Every model score (CLIP similarity, Smaug AI-image score, Wav2Vec2
   deepfake-audio score, ManTraNet anomaly map) is evidence, not proof.
3. **Evidence must be traceable.** Every finding records: source URL, model name + version,
   raw score, timestamp. This is what Module 7 (Fusion/Explanation) renders back to the user.
4. **Fail honest, not silent.** An unavailable model/API is reported as `not_assessed`, never
   defaulted to a score.
5. **[Improvement] Guard against the agent's own failure modes**, not just the media's:
   - *Echo-chamber detection* (Veritas) — don't let 3 copies of the same wire story inflate
     confidence in Module 6's web evidence.
   - *Essence/claim drift guard* (Veritas) — don't let claim extraction (OCR text, Whisper
     transcript → LLM-extracted claims) silently drift from what the image/video actually shows.
   - *Adversarial (two-sided) search* (Veritas) — every claim gets both a confirming and a
     contradicting query; never just "search and see what comes back."
6. **Evaluate before trusting.** Every detector needs a labeled held-out set and a reported
   false-positive/negative rate before it's allowed to move a confidence score (document_forgery
   §"Performance Targets" is the right shape: accuracy, FPR, latency, throughput targets per
   module).

---

## 2. High-Level System Diagram

```mermaid
graph TB
    subgraph Client
        WEB[Next.js Frontend]
    end

    subgraph Gateway
        API[FastAPI Gateway<br/>upload, status, results]
    end

    subgraph Queue["Async Job Layer"]
        Q[(Redis — ARQ queue + 7-day SHA-256 result cache)]
    end

    subgraph Orchestrator["LangGraph Orchestrator (Module 1)"]
        ROUTE[Input Router<br/>text+image / video / audio-only]
    end

    subgraph ImagePipe["Module 2 — Image Intelligence"]
        BLIP[BLIP Caption]
        CLIP[CLIP Claim-Image Similarity]
        OCR[PaddleOCR]
        AIGEN[Smaug AI-Image Detector]
        MANIP[Manipulation Localization<br/>ManTraNet/BusterNet-style]
    end

    subgraph VideoPipe["Module 3 — Video Intelligence"]
        FRAMES[Frame + Audio Extraction<br/>FFmpeg/OpenCV]
        TRISTREAM[Tri-Stream Deepfake Engine<br/>Spectral + Spatial(ViT) + rPPG]
    end

    subgraph AudioPipe["Module 4 — Audio Forensics"]
        WHISPER[Whisper Transcription]
        DEEPAUD[Synthetic-Audio Detector<br/>Wav2Vec2 / AASIST]
        SYNC[Optional: SyncNet A/V sync]
    end

    subgraph TextPipe["Module 2B — Synthetic Text Detection"]
        SYNTEXT[AI-generated-text Scorer]
    end

    subgraph ReusePipe["Module 5 — Historical Reuse"]
        HASH[SHA-256 + pHash]
        REVERSE[Optional: Reverse-image search]
    end

    subgraph FactPipe["Module 6 — Fact-Checking Engine"]
        SPLIT[Claim Splitter + Drift Guard]
        ADV[Adversarial Tavily Search<br/>+ Echo-Chamber Detection]
        NLI[NLI Evidence Judge<br/>DeBERTa]
    end

    subgraph FusionPipe["Module 7 — Fusion + Explanation"]
        FUSE[Two-Level Fusion<br/>rules + weighted/ML fusion]
        EXPLAIN[Evidence-Grounded Explanation<br/>Gemini]
    end

    subgraph Store["Storage"]
        PG[(Postgres + pgvector<br/>reference hashes, results, embeddings)]
        OBJ[(Object storage<br/>media, heatmaps)]
    end

    WEB --> API --> Q --> ROUTE
    ROUTE --> ImagePipe
    ROUTE --> VideoPipe
    VideoPipe --> ImagePipe
    VideoPipe --> AudioPipe
    ImagePipe --> ReusePipe
    VideoPipe --> ReusePipe
    ImagePipe --> FactPipe
    VideoPipe --> FactPipe
    AudioPipe --> FactPipe
    ROUTE --> TextPipe
    ImagePipe --> TextPipe
    AudioPipe --> TextPipe
    TextPipe --> FusionPipe
    ImagePipe --> FusionPipe
    VideoPipe --> FusionPipe
    AudioPipe --> FusionPipe
    ReusePipe --> FusionPipe
    FactPipe --> FusionPipe
    FusionPipe --> PG
    FusionPipe --> OBJ
    API --> PG
```

Orchestration note: use **LangGraph's `Send` API fan-out/fan-in** (the pattern Veritas uses for
parallel per-claim subgraphs) at two levels: (a) fan out the independent modality branches
(image / video-frames / audio) that all run concurrently, and (b) inside Module 6, fan out one
subgraph per extracted claim, exactly as Veritas does. This is a direct, proven pattern to
reuse — not something to redesign.

---

## 3. Module Map

### Module 1 — Ingestion & Orchestration

**Purpose:** Accept text+image / video / audio submissions, normalize them, dispatch to the
right modality branches, and hold the whole run together as one `GraphState`.

**Reused patterns:**
- Veritas's `agent/pipeline.py` + `agent/nodes.py` shape (a `StateGraph` with typed state in
  `schema/state.py`) is the right skeleton — reuse the *pattern*, not the fact-checking content.
- document_forgery's task-dispatch idea (`[preprocess → analyze_parallel → fuse → report]`) maps
  cleanly onto LangGraph nodes instead of a Celery chain.
- **[Improvement]** Veritas's **SHA-256 cache-check-first node**: hash the raw upload, check
  Postgres/Redis before doing any inference. Directly saves cost on repeat/viral content, and
  this project will see the same submission multiple times during a demo/hackathon judging round.

**New work:** input-type router (text+image vs. video vs. audio-only), `GraphState` schema
covering all modules' outputs (superset of the video spec's JSON contract in §4 of
`video_forensics_tech_spec.md` and Veritas's claim schema).

**Decision — task queue:** use **ARQ + Redis** (Veritas's choice), not Celery
(document_forgery's choice). Reasoning: everything here is inference, not training; ARQ's native
asyncio integration with FastAPI is a better fit than Celery's broker/worker split, and it's one
fewer moving part for a time-boxed build. Fall back to Celery only if a GPU-bound video module
needs dedicated long-running worker processes with retry/rate-limiting semantics ARQ doesn't give.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | `GraphState` TypedDict + Pydantic output models for every module (contract-first) |
| 2 | FastAPI `/api/v1/analyze` endpoint: validate upload, hash, cache-check, enqueue |
| 3 | ARQ worker entrypoint running the compiled LangGraph |
| 4 | Input router node (text+image / video / audio-only branch selection) |
| 5 | Redis-backed 7-day result cache keyed by SHA-256, wired into the cache-check node |

---

### Module 2 — Image Intelligence
*(= Module A in `multimodal_misinformation_module_guide.md`)*

**Purpose:** For an image (standalone, or a video keyframe), answer: what's in it, does it match
the claim, what text is written on it, is it AI-generated, is it manipulated.

| Sub-task | Model | Status |
|---|---|---|
| Caption | BLIP base (`Salesforce/blip-image-captioning-base`) | New integration, local HF Transformers |
| Claim-image similarity | CLIP ViT-B/32 | New integration |
| Embedded text | PaddleOCR | New integration |
| AI-generated detection | Smaug AI Image Detector | New integration |
| Manipulation localization | **Reuse `document_forgery`'s zero-shot ManTraNet/BusterNet pipeline** (`app/backend/imageforensic/member2_spatial_forensics.py`) | **Reuse as-is** — never fine-tuned on documents, so it transfers to natural photos with no retraining. Validate on a natural-image test set before trusting it (per Guiding Principle 6). |

**[Improvement] Widen PaddleOCR's scope beyond embedded caption text.** A3 originally only reads
meme/poster/screenshot text. Extend the same OCR call to also read incidental background text —
street signs, storefronts, license plates, banner language — and pass that text onward to Module
6 as location/context evidence, not just as a fact-checkable caption. This is a scope change to
an existing call, not a new model.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | Port `member2_spatial_forensics.py` out of `document_forgery`, run it against ~50 labeled natural (non-document) images, confirm it still separates tampered/clean |
| 2 | Wrap BLIP + CLIP + PaddleOCR as plain Python functions (no LangChain adapters — per guide's integration principle) |
| 3 | Integrate Smaug detector, record Apache-2.0 attribution |
| 4 | Single `analyze_image(image, claim_text) -> ImageFindings` entrypoint used directly by Module 2 and per-frame by Module 3 — isolated, no dependency on Module 1/6/7 internals (see §6) |

---

### Module 2B — Synthetic Text Detection
*(new — closes Deliverable 4's "text" gap, which no existing doc addresses)*

**Why this exists:** Deliverable 4 names three synthetic-media types — **text, images,
deepfakes**. The guide and the video spec build detectors for the other two (Smaug for images,
the tri-stream engine + Wav2Vec2 for video/audio) but neither has anything that scores whether a
text artifact itself was LLM-generated. This module fills exactly that gap, and only that gap —
it does not duplicate Module 6's claim-verification job (is the *content* true); it only asks
whether the *text itself* looks machine-written.

**Purpose:** Given any text artifact flowing through the pipeline — the raw caption, Module 2's
OCR output, or Module 4's Whisper transcript — score the likelihood it was AI-generated, as an
independent, isolated signal.

**Design:**
- **Primary model:** a pretrained AI-text classifier (e.g. a RoBERTa-based open-source detector)
  run locally, no per-call API cost.
- **Secondary/cross-check signal:** a perplexity-ratio ("Binoculars"-style) zero-shot check using
  two small off-the-shelf causal LMs — catches generated text the classifier head was never
  trained on, at the cost of extra local inference.
- **Length gate, per Guiding Principle 4 (fail honest):** these detectors are unreliable on short
  text. Below a minimum token count (e.g. OCR meme captions, short alt-text), return
  `not_assessed` rather than a confident score — don't let a 5-word caption produce a misleading
  "87% AI-generated" number.
- **Output contract:** `SyntheticTextFindings { score: float, verdict: ai_likely | human_likely |
  inconclusive | not_assessed, method, source: caption|ocr|transcript, text_length }`.
- **Signal, not verdict** (Guiding Principle 2) applies with extra force here — AI-text detectors
  have well-documented false-positive rates on non-native-English writing and short-form text;
  this score feeds Module 7's fusion as one input among several, never a standalone fake/real call.

**Isolation (per §6):** this module takes a plain string and a `source` tag, returns
`SyntheticTextFindings`, and has zero knowledge of which module produced the text or what happens
to the score afterward. It is callable identically whether the text came from Module 1's raw
caption, Module 2's OCR, or Module 4's transcript.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | Define the `TextInput`/`SyntheticTextFindings` contract (length, source tag, score, verdict) |
| 2 | Wire in the pretrained AI-text classifier as the primary scorer |
| 3 | Add the length gate → `not_assessed` path |
| 4 | (Stretch) Add the perplexity-ratio cross-check as a second method, surfaced alongside the classifier score rather than replacing it |
| 5 | Single `detect_synthetic_text(text, source) -> SyntheticTextFindings` entrypoint, called from wherever Module 1/2/4 produce text — no inverse dependency |

---

### Module 3 — Video Intelligence
*(= Module B in the guide + the tri-stream engine in `video_forensics_tech_spec.md`)*

**Purpose:** Preprocess video into frames + audio, run Module 2 on sampled frames, and run a
dedicated deepfake-specific tri-stream engine on detected faces.

**Pipeline (per `video_forensics_tech_spec.md`):**
1. **Dense snippet extraction** — three 30-frame windows at 10/50/90% of duration (`cv2.VideoCapture`), not all frames (avoids the RAM blowup the spec explicitly warns about).
2. **Face alignment** — MediaPipe FaceMesh, 468 landmarks, 15% bbox padding to catch jaw/neck blending seams.
3. **Tri-stream forensics**, fused by weighted peak (not average):
   - **Spectral — split into two sub-features, not one score `[fix]`:** the spec's original
     design runs a single 2D-DCT high-frequency corner-energy check and feeds it into *both* the
     AI-generation verdict and an `adversarial_status` field. Those are different claims about
     the input and the same raw energy measurement can't honestly support both, so decompose the
     same DCT output into two separable signals instead of adding a new model:
     - `spectral_artifact_score` — energy concentrated in a **periodic checkerboard** pattern at
       a frequency tied to a generator's upsampling stride → genuine GAN/diffusion evidence, feeds
       the **media-authenticity** axis (Deliverable 4).
     - `signal_integrity_score` — **broadband, non-periodic** high-frequency energy (the
       signature of recompression, re-encoding, or adversarial noise, none of which imply
       synthetic *content*) → feeds a confidence caveat, never a generation verdict (Deliverable 6).
     - **Precedence rule:** if `signal_integrity_score` is high, don't also assert a confident
       `spectral_artifact_score` verdict — emit `confounded_by_recompression: true` and downgrade
       to `inconclusive` instead, per Guiding Principle 4. This matters even outside adversarial
       scenarios: ordinary reposted/re-encoded real video raises broadband high-frequency energy
       too, and without this split it would get misread as "AI-generated."
   - **Spatial:** ViT (`SiglipForImageClassification`) + attention-rollout, intersected with
     MediaPipe landmarks → produces the human-readable string ("anomaly localized at the lower
     chin boundary") that satisfies the explanation deliverable directly from the detector, not
     from a post-hoc LLM guess.
   - **Biometric (rPPG):** forehead green-channel signal, bandpass 0.7–2.5 Hz, FFT peak check —
     "deepfakes are biologically dead."
4. **General frame analysis** — run Module 2's `analyze_image` on the same sampled frames
   (caption/CLIP/OCR/Smaug), timestamped.
5. **Output:** the JSON contract from `video_forensics_tech_spec.md` §4 (`verdict`,
   `confidence_score`, `forensic_streams`, `flagged_segments_sec`, `concrete_evidence[]`,
   `saliency_heatmap_path`), **with one deliberate deviation from the spec as written:**
   `forensic_streams.spectral_artifact_detected` is replaced by the two separated fields above
   (`spectral_artifact_score`, `signal_integrity_score`) plus `confounded_by_recompression`, and
   `adversarial_status` is now driven only by `signal_integrity_score`. Everything else — the
   `concrete_evidence[]` array being handed straight to the explanation LLM, the saliency heatmap
   — carries over unchanged.

**[Improvement]** The spec's rPPG + spectral + spatial fusion only covers **face-swap/diffusion
deepfakes**. It does not cover *re-encoded/cropped real footage reused out of context* — that's
Module 5's job on the same keyframes, not this module's. Keep the boundary explicit in code: this
module answers "was this footage synthetically generated," Module 5 answers "has this footage
appeared before." Don't let one module's `verdict` field get overloaded to mean both.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | FFmpeg/OpenCV snippet extraction + audio demux |
| 2 | MediaPipe face-mesh + padded crop pipeline |
| 3 | Spectral stream — compute the DCT, then split corner energy into the periodic (`spectral_artifact_score`) and broadband (`signal_integrity_score`) sub-features above; cheapest stream, build first |
| 4 | rPPG stream (bandpass + FFT) |
| 5 | Spatial ViT + attention rollout + landmark-to-text mapping (most complex — needs a labeled deepfake set, e.g. FaceForensics++/DFDC, to validate thresholds) |
| 6 | Weighted-peak fusion → the JSON contract above |
| 7 | Wire Module 2's `analyze_image` onto the same sampled frames |

---

### Module 4 — Audio Forensics
*(= Module B3–B6 in the guide)*

**Purpose:** Transcribe spoken claims, score the audio for synthetic/deepfake signals, and
optionally check audio/video sync.

| Sub-task | Model | Notes |
|---|---|---|
| Transcription | Whisper `small` / faster-whisper | Feeds Module 6 as the claim source for video |
| Synthetic-audio detection | `mo-thecreator/Deepfake-audio-detection` (Wav2Vec2) | **Start here** — directly carried over from the SecureVox reference project per the guide's recommendation |
| Alternative detector | AASIST | Only benchmark if time + labeled data allow; not required for MVP |
| A/V sync (optional) | SyncNet | Cross-checked against Module 3's `flagged_segments_sec` — a visual anomaly *and* a lip-sync failure at the same timestamp boosts combined confidence (per `video_forensics_tech_spec.md` §5) |

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | FFmpeg audio extraction → mono 16kHz WAV |
| 2 | Whisper transcription → claim text handed to Module 6 |
| 3 | Wav2Vec2 deepfake-audio scorer, labeled `synthetic_audio_signal_detected` / `no_strong_signal_detected` / `inconclusive` — never a binary real/fake claim |
| 4 | (Optional, time-permitting) SyncNet cross-check against Module 3 timestamps |

---

### Module 5 — Historical / Out-of-Context Reuse
*(= Module A6/B7 in the guide; **the most complete module on day one**)*

**Purpose:** Has this exact or visually-similar media appeared before, under a different story?

**Reused assets — reuse as-is, no retraining needed:**
- **SHA-256 + pHash fingerprinting**, directly from `document_forgery`'s ingestion/blockchain
  module — Hamming-distance tiers (<5 same, 5–15 modified, >15 different) carry over unchanged.
  This single component covers the guide's "historical image reuse" and "historical video
  reuse" sub-modules for both Module 2 and Module 3's keyframes.
- Reference-image store: hash + known source URL + date + caption, same shape document_forgery
  already uses for its blockchain hash registry — **minus the blockchain itself**. Misinformation
  provenance doesn't need an immutable on-chain ledger the way document legal-defensibility does;
  a Postgres table with the hash, pHash, source metadata, and insertion timestamp is sufficient
  and much faster to ship. (Explicit scope cut vs. document_forgery's Module 6.)

**Optional extension:** SerpApi Google Lens reverse-image search for matches outside the local
reference store — gate behind a feature flag since it's a paid external call.

**[Improvement] Return structured source metadata, not just a reuse flag.** Today this module's
contract is effectively binary (`reused: true/false` + hamming distance tier). Change the output
to also carry whatever the matched source actually states — `source_url`, `source_published_at`,
`source_location` (if stated on the matched page/article) — even when no reverse-image API is
enabled, since the local `reference_media` table already stores `source_url`/`published_at`.
This is what lets Module 6 cross-check the *claim's* stated date/location against the *media's
actual* first-known date/location (see Module 6 below) without adding any new model — it's a
contract change on an existing lookup, not new work.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | Port the hash/pHash code out of document_forgery's ingestion module |
| 2 | Postgres `reference_media` table (hash, phash, source_url, published_at, caption, modality) |
| 3 | Seed it with a small curated set of known viral/reused media for the demo |
| 4 | Lookup function callable from both Module 2 and Module 3's keyframe loop |
| 5 | (Optional) SerpApi client behind a flag, with its own rate/cost guard |

---

### Module 6 — Fact-Checking & Evidence Engine
*(= Module C1–C3 in the guide, rebuilt on Veritas's pipeline, not the guide's flatter sketch)*

**Purpose:** Given a claim (from a caption, OCR text, or a video transcript), gather evidence and
judge whether it's supported, contradicted, or unverifiable.

**The guide's version of this module (Tavily search → DeBERTa NLI) is a reasonable sketch but
is missing every safety mechanism Veritas already built and validated in production.
Adopt Veritas's per-claim subgraph wholesale:**

1. **Claim splitting** (if the module needs multiple atomic claims from one caption/transcript) —
   reuse Veritas's `type: fact | framing | attributed` tagging and `loaded_language` extraction;
   both are directly useful for the misinformation explanation deliverable, not just claim
   checking. **[Improvement]** Extend the splitter's tagging with standard NER so each claim also
   carries structured `location` / `datetime` / `named_people` / `event` fields, not just the
   `fact|framing|attributed` type. This is what makes the cross-modal check in point 7 below
   possible — without entity tags there's nothing concrete to cross-reference against Module 5's
   source metadata.
2. **[Improvement] Essence Drift Guard** — cosine-similarity check (local
   `sentence-transformers`, no API cost) between the original caption/transcript and the
   recomposed extracted claims. The guide has no equivalent safeguard; without it, a bad OCR read
   or a bad Whisper transcript silently becomes the "claim" that gets fact-checked, and nobody
   notices.
3. **Query builder → adversarial search** — two Tavily queries per claim (confirming +
   contradicting), run concurrently via `asyncio.gather`, same as Veritas.
4. **[Improvement] Echo-Chamber Detection** — flag when 3+ results share a root domain or fewer
   than 3 unique domains appear total; apply a confidence multiplier (Veritas uses 0.75×). The
   guide's Design Rule 3 ("historical matching needs source context") implicitly wants this for
   Module 5 too — apply the same domain-diversity check there.
5. **Evidence Judge** — merge the guide's DeBERTa NLI step with Veritas's single structured
   LLM-judge call: classify each evidence item by relevance/stance/source-type, then render
   `supported | contradicted | uncertain | unverifiable`. Use DeBERTa NLI as a cheap local
   pre-filter (relevance/stance) before the one LLM call does the final judgment — this keeps the
   per-claim LLM cost at Veritas's "single merged call" level while adding a free local
   cross-check the guide wanted.
6. **Google Fact Check Tools API** — supplementary lookup, as the guide specifies; feed its hits
   into the same evidence set the Evidence Judge scores.
7. **[Improvement] Entity-level cross-modal consistency, built from cross-connections rather than
   new models.** This closes the Deliverable-2 gap that CLIP alone (A2) can't: a genuine photo of
   a real event, captioned with the wrong place/date, still scores *high* on CLIP because the
   scene matches — the mismatch is in the specific facts, not the visual category. Rather than
   adding dedicated geolocation/chronolocation/face-verification models, wire together signals
   already in the pipeline:
   - Compare the claim's NER-tagged `location`/`datetime`/`named_people` (point 1) against
     Module 5's `source_published_at`/`source_location`, when a reverse-image/local-store match
     exists. A contradiction here (claim says "yesterday," matched source is from 2019) is
     stronger, cheaper evidence than any pixel-level inference.
   - Fold the widened-scope OCR text from Module 2 (street signs, storefronts, banner language)
     into the query sent to point 3's adversarial search, as extra disambiguating context.
   - Build an **entity × signal agreement matrix** instead of collapsing straight to one score:
     where two independent signals (e.g. Module 5's source date vs. a Tavily search result's
     stated date) *disagree with each other*, surface that as its own flag — independent of
     whether either one agrees with the claim.
   - When no source is found anywhere (Module 5 empty, Tavily empty), the entity-level check
     reports `unverifiable`, not a guess. This is the explicit tradeoff of staying shallow: it
     reliably catches *reused* media with a findable prior source, and is honest about not
     catching a genuinely novel wrong-context fabrication that's never been posted before.
   - This produces exactly the structured, per-entity evidence (not a bare similarity number) a
     downstream explanation/XAI layer needs to cite concretely — e.g. "claim states Location A;
     the matched source places this photo in Location B, published 2019" — per Guiding
     Principle 3 (evidence must be traceable).

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | Port Veritas's `agent/llm_judge_subgraph.py` + `services/web_search.py` + `services/essence_guard.py` wholesale as the starting point |
| 2 | Swap Veritas's article-essence framing for this project's claim sources (OCR text / caption / Whisper transcript) |
| 3 | Add Google Fact Check Tools API as a second evidence source feeding the same judge |
| 4 | Wire DeBERTa NLI in as a pre-filter ahead of the LLM judge call |
| 5 | Reuse Veritas's SHA-256 7-day cache at the claim level (separate from Module 1's media-level cache) |
| 6 | Add NER entity-tagging to the claim splitter's output schema |
| 7 | Wire Module 5's `source_url`/`source_published_at`/`source_location` into the Evidence Judge's input as an additional evidence item, and build the entity × signal agreement check |

---

### Module 7 — Fusion, Aggregation & Explanation
*(= Module C4 in the guide, structurally borrowed from document_forgery's Module 5, with
Veritas's explanation-writing discipline)*

**Purpose:** Combine every module's independent findings into one report with separate verdicts
per axis (claim veracity / media authenticity / cross-modal consistency / historical reuse) and a
plain-language explanation — never a single fake/real label.

**Fusion strategy — adapt document_forgery's two-level fusion, but keep the four axes separate
instead of collapsing to one forgery score:**
- **Level 1 (rules):** any single detector at extreme confidence (e.g., Smaug > 0.95, or an
  exact SHA-256 historical match) short-circuits that *axis* to a strong verdict without waiting
  on ML fusion — same early-exit idea as document_forgery's pre-fusion rules.
- **Level 2 (weighted/ML fusion per axis):** within each axis, concatenate that axis's module
  scores into a small feature vector and fuse (start with the guide's weighted-average approach
  from Veritas's `Score Aggregator`; upgrade to a small XGBoost head per axis later if labeled
  fusion data becomes available — document_forgery's choice of XGBoost-for-explainability is the
  right fallback, not a mandatory day-one build).
- **Do not fuse across axes.** A high manipulation score and a low claim-veracity score are two
  separate findings in the final report, exactly per Guiding Principle 1.
- **Consume Module 3's split spectral signals separately, not as one input.** `spectral_artifact_score`
  feeds the media-authenticity axis like any other detector score; `signal_integrity_score` and
  `confounded_by_recompression` are not an axis input at all — they're a confidence modifier
  applied to the authenticity axis's own output, so a recompressed-but-real video degrades to
  `inconclusive` rather than fusing in as evidence of either "fake" or "real."

**Explanation generation** — reuse Veritas's discipline, not the guide's vaguer "optional Gemini"
note:
- Pass the structured, already-validated evidence (per-axis verdicts + `concrete_evidence[]`
  strings from Module 3 + evidence-judge reasoning from Module 6) directly into the prompt.
  **Never let the LLM guess why something is flagged** — `video_forensics_tech_spec.md` §5 says
  this explicitly for the video engine, and Veritas's Node 11 does the same thing for claims;
  apply it project-wide.
- Output: 3–4 sentence summary covering what was verified true, what was contradicted (naming
  the specific false detail when available), what couldn't be checked, and how manipulation/reuse
  findings affect the overall picture.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | Define the 4-axis output schema (veracity / authenticity / cross-modal / historical), each with its own verdict + confidence + evidence list |
| 2 | Level-1 rule short-circuits per axis |
| 3 | Level-2 weighted fusion per axis (Veritas-style weighted average first) |
| 4 | Explanation prompt consuming only validated structured evidence, modeled on Veritas Node 11 / the video spec's prompt example |
| 5 | Render saliency heatmap + evidence citations in the API response |

---

### Module 8 — Evaluation & Robustness Harness
*(new — closes the single largest gap identified in `ml_exisitng_assets.md` §3)*

**Why this is its own module, not an afterthought:** `ml_exisitng_assets.md` is explicit that
*nothing* in the reusable stack includes a quantitative eval harness or adversarial-robustness
testing, and the guide's Guiding Principle 7 ("evaluate before trusting") has no home without
one. Both reference projects treat this as a late-stage task; building it as its own module from
day one means every other module ships with a number attached, not a vibe.

**Scope:**
- Labeled test sets per module: natural-image manipulation (for Module 2's ported ManTraNet),
  deepfake video (FaceForensics++/DFDC subset, for Module 3), synthetic audio (for Module 4), a
  small claim/evidence set (for Module 6).
- Standard metrics per module: accuracy/F1, false-positive rate on genuine media, latency —
  mirrors document_forgery's "Performance Targets" table structure, applied per-module here
  instead of to one end-to-end forgery score.
- **Adversarial robustness pass:** re-encode/recompress/crop test media and re-run; this is the
  dimension `ml_exisitng_assets.md` flags as entirely untested in the inherited stack.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | Pull/curate small labeled sets per module (reuse CASIA/FaceForensics++/ASVspoof-style public sets where licensing allows) |
| 2 | Per-module eval script producing accuracy/F1/FPR/latency |
| 3 | Augmentation/robustness pass: recompress at JPEG 60–100, re-encode video at 2 bitrates, crop/rescale images, re-run Module 2/3/4 and diff the verdicts |
| 4 | One `eval_report.json` per module, surfaced in the frontend's analytics view for judging/demo credibility |

---

### Module 9 — API, Storage & Frontend

**Backend (FastAPI, already scaffolded in `backend/app/main.py`):**

```
POST /api/v1/analyze              → upload (image/video/audio+claim), returns job_id
GET  /api/v1/results/{job_id}     → poll status / full structured result
GET  /api/v1/results/{job_id}/report   → rendered explanation + evidence
GET  /api/v1/reference/lookup     → manual hash/pHash lookup against Module 5's store
GET  /api/v1/eval/{module}        → Module 8's latest eval report, for the demo dashboard
```

**Storage decision: Supabase** (managed Postgres + pgvector + Storage + Auth), not Firestore
(Veritas) and not document_forgery's heavier Supabase+IPFS+Ethereum stack. Reasoning:
- One managed service gives the relational DB (`jobs` → per-module findings → evidence sources),
  pgvector (claim-embedding drift guard, future "similar past claims" lookup), *and* object
  storage (media files, heatmaps, saliency overlays) — no separate S3-compatible service to stand
  up, and no self-hosted Postgres container to manage.
- This project has no blockchain/legal-provenance requirement, so document_forgery's IPFS +
  Ethereum layer is cut entirely — Supabase Storage is sufficient for media/report artifacts.
- Supabase Auth is available for free if the frontend ever needs user accounts (e.g. a reviewer
  login for Module 8's analytics view) without adding a separate auth service.
- Redis stays in the stack *only* for the ARQ job queue (Supabase doesn't provide a queue) — do
  not route job-queue traffic through Supabase Postgres; keep that concern separate from the data
  layer. (Stretch: Postgres-native queueing, e.g. `pgmq`, could drop the Redis dependency entirely
  once the demo is stable — not a day-one concern.)

**Frontend: Next.js stays** (already scaffolded in `frontend/`) over Veritas's React+Vite choice
— it's already in this repo, and its built-in routing/SSR is a better fit than a reference-app
swap would justify. Upload form → job-status poll → result view with: per-axis verdict cards
(styled like Veritas's `ClaimCard.tsx`), a confidence breakdown (styled like document_forgery's
radar chart idea), the saliency heatmap overlay from Module 3, and the final plain-language
explanation from Module 7.

**Implementation plan:**
| Step | Deliverable |
|---|---|
| 1 | `GraphState` → Pydantic response models → FastAPI routes above |
| 2 | Supabase schema: `jobs`, `module_findings`, `reference_media`, `evidence_sources`; Supabase Storage buckets for media/heatmaps |
| 3 | Upload + polling UI (reuse Veritas's job-poll pattern) |
| 4 | Result view: axis cards + confidence breakdown + heatmap + explanation |
| 5 | Demo analytics view surfacing Module 8's eval reports |

---

## 4. Asset Reuse Matrix

Condensed from `ml_exisitng_assets.md`, with exact source paths for what's actually being ported.

| Asset | Source path | Disposition | Target module |
|---|---|---|---|
| ManTraNet/BusterNet spatial forensics (VGG16 + ResNet50, zero-shot) | `document_forgery/app/backend/imageforensic/member2_spatial_forensics.py` | **Reuse as-is** | Module 2 |
| SHA-256 + pHash fingerprinting | document_forgery ingestion/blockchain module | **Reuse as-is** | Module 5 |
| Gemini semantic-validation call pattern | `document_forgery/app/backend/ml/inference/text_forensics_engine.py` | **Reuse as-is** (pattern) | Module 6 / Module 7 explanation |
| Swin-Transformer backbone | `document_forgery/doc_forg_wts/backend/ml/weights/swin_base_backbone.safetensors` | Keep backbone, discard document head, retrain for natural-image manipulation localization | Module 2 (stretch) |
| EfficientNet-B0 backbone | `.../efficientnet_b0_backbone.safetensors` | Keep backbone, discard font-classifier head, retrain as lightweight GAN-artifact classifier | Module 2/3 (stretch) |
| LangGraph `StateGraph` + per-claim `Send` fan-out pattern | `Veritas/backend/agent/pipeline.py`, `nodes.py` | **Reuse pattern** | Module 1, Module 6 |
| Adversarial search + Evidence Judge subgraph | `Veritas/backend/agent/llm_judge_subgraph.py`, `services/web_search.py` | **Port wholesale, re-target claim source** | Module 6 |
| Essence Drift Guard | `Veritas/backend/services/essence_guard.py` | **Reuse as-is** | Module 6 |
| SHA-256 7-day result cache | `Veritas` cache-check node + Firestore cache | **Reuse pattern**, backed by Postgres/Redis instead | Module 1, Module 6 |
| Two-level fusion (rules + ML) | document_forgery §Module 5 | **Reuse pattern**, split per-axis instead of single score | Module 7 |
| `logo.pt` YOLO detector | `document_forgery/doc_forg_wts/backend/ml/weights/logo.pt` | Marginal — only if brand/logo impersonation is in scope; needs social-media fine-tuning first | Module 2 (optional) |
| `signature.pt`, `stamp.pt`, `handwriting.pt`, DTD model/head, font-classifier head | document_forgery weights | **Discard** — document-specific, no misinformation equivalent | — |
| Image deepfake/GAN detector, video deepfake detector, dedicated CLIP cross-modal scorer, AI-generated-text detector, adversarial-robustness harness, quantitative eval harness | — (none exist in either reference repo) | **Build from scratch** | Modules 2/3 (Smaug + tri-stream engine fill the first two), Module 2 (CLIP), **Module 2B (text)**, Module 8 (robustness/eval) |

---

## 5. Build Order

Reconciling the guide's 3-phase order with the module split above:

1. **Phase 1 — Image pipeline:** Module 1 (basic ingest, no cache yet) → Module 2 (BLIP, CLIP,
   OCR, Smaug, ported ManTraNet) → **Module 2B (AI-text classifier, no perplexity cross-check
   yet)** → Module 5 (hash/pHash) → Module 6 (claim splitting + adversarial search, skip drift
   guard/echo-chamber/entity cross-check first pass) → Module 7 (rules-only fusion, no ML fusion
   yet) → Module 9 (upload → result, no polling needed yet since image path is fast).
2. **Phase 2 — Video + audio:** Module 3 (frame/audio extraction, tri-stream engine) reusing
   Module 2 per-frame, Module 4 (Whisper + Wav2Vec2), Module 5 extended to keyframes, Module 1's
   ARQ queue + polling now load-bearing since video is slow.
3. **Phase 3 — Hardening:** Module 6's drift guard + echo-chamber detection + entity-level
   cross-modal check (wiring Module 5's source metadata into Module 6), Module 7's per-axis
   weighted/ML fusion + explanation generation, Module 8 (eval harness across every module built
   so far), Module 1's result cache.
4. **Phase 4 — Stretch:** SyncNet A/V sync cross-check, SerpApi reverse-image search, Module 2B's
   perplexity-ratio cross-check, retrained Swin/EfficientNet heads for natural-image
   manipulation/GAN detection, logo/brand detector.

---

## 6. Modular Design & Orchestration Strategy

**Principle:** every module in §3 (2, 2B, 3, 4, 5, 6, 7, 8) is built, tested, and runnable as a
**standalone unit before any orchestration framework exists**. A module takes typed input,
returns typed output, and knows nothing about any other module or about LangGraph/LangChain/ARQ.
Orchestration is strictly external — it is wiring between modules, never logic inside one.

**Contract-first convention:**
- Each module owns its own `contracts.py` (Pydantic input/output models, e.g.
  `ImageInput`/`ImageFindings`, `TextInput`/`SyntheticTextFindings`) and exposes exactly one
  public entrypoint — `run(input: <Module>Input) -> <Module>Output` (sync or async). That
  function is the module's *entire* interface surface.
- Every module must be exercisable directly — a script, a notebook cell, or a unit test calling
  `run()` with a sample input — with zero orchestration framework installed. That's what makes
  "isolated, completes its given task" a literal property of the code, not a design aspiration.
- No module imports another module's internals. Module 3 *calls* Module 2's `run()` as a plain
  function (per-frame), but never reaches into Module 2's internal state — the same discipline
  that will later let the orchestrator call it as a graph node instead.

**Why defer orchestration rather than build it alongside each module:**
- Mirrors document_forgery's own stated risk mitigation ("microservice architecture allows
  independent development; mock interfaces early") — different people/sessions can build Modules
  2, 4, and 6 in parallel against the agreed contracts without touching a shared graph file.
- Keeps the orchestration layer swappable without touching module code. The contracts don't
  change whether the wiring ends up being **LangGraph** (primary recommendation — reuses Veritas's
  `StateGraph`/`Send` fan-out pattern already referenced in §2), **LangChain**'s tool-calling/
  agent abstractions (reserved specifically for sub-tasks that need a ReAct-style loop — e.g. if
  Module 7's explanation step should be able to *ask* for more evidence mid-generation rather
  than receive it all upfront), or plain `asyncio.gather` for an early demo cut before LangGraph
  is wired in at all.

**Build sequence for the orchestration layer itself (comes *after* modules exist, not before):**
1. Stand up the thinnest possible LangGraph `StateGraph`: Module 1's router node wired to exactly
   one modality branch (e.g. Module 2's `run()` called directly as a node function). This
   validates the wiring pattern early — don't wait until every module is "done" to write the
   first orchestration node.
2. Add each remaining module to the graph as it stabilizes, one node per module's `run()`. The
   node wrapper does nothing but call `run()` and place the result in `GraphState` — no logic
   duplicated into the node.
3. Reuse Veritas's `Send`-based fan-out at the two genuinely parallel points: the top-level
   modality branches (image / video / audio, all independent) and Module 6's per-claim subgraph.
4. Module 7 (Fusion) is the one node allowed to depend on more than one module's output type,
   since combining them *is* its job. Every other node depends on exactly one module's contract.

---

## 7. Proposed Directory Structure

```
nith/
├── docs/
│   ├── architecture.md                      # this file
│   ├── multimodal_misinformation_module_guide.md
│   ├── video_forensics_tech_spec.md
│   └── ml_exisitng_assets.md
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── supabase_client.py           # Supabase (Postgres+pgvector+Storage) client
│   │   │   └── cache.py                     # Redis / SHA-256 cache helpers (ARQ queue only)
│   │   ├── api/v1/
│   │   │   ├── analyze.py
│   │   │   ├── results.py
│   │   │   ├── reference.py
│   │   │   └── eval.py
│   │   ├── orchestrator/                    # the ONLY place that imports LangGraph
│   │   │   ├── state.py                     # GraphState schema
│   │   │   ├── pipeline.py                  # LangGraph StateGraph wiring module run()s as nodes
│   │   │   └── router_node.py
│   │   ├── modules/                         # each subfolder is standalone — no cross-imports
│   │   │   ├── image/                       # Module 2
│   │   │   │   ├── contracts.py  caption.py  similarity.py  ocr.py  ai_detect.py  manipulation.py
│   │   │   ├── text/                        # Module 2B
│   │   │   │   ├── contracts.py  synthetic_text.py
│   │   │   ├── video/                       # Module 3
│   │   │   │   ├── contracts.py  extraction.py  tristream_spectral.py  tristream_spatial.py  tristream_rppg.py  fusion.py
│   │   │   ├── audio/                       # Module 4
│   │   │   │   ├── contracts.py  transcribe.py  deepfake_audio.py  av_sync.py
│   │   │   ├── reuse/                       # Module 5
│   │   │   │   ├── contracts.py  hashing.py  reference_store.py  reverse_search.py
│   │   │   ├── factcheck/                   # Module 6
│   │   │   │   ├── contracts.py  claim_splitter.py  drift_guard.py  web_search.py  evidence_judge.py  fact_check_api.py
│   │   │   ├── fusion/                      # Module 7
│   │   │   │   ├── contracts.py  rules.py  weighted_fusion.py  explanation.py
│   │   │   └── eval/                        # Module 8
│   │   │       ├── contracts.py  harness.py  robustness.py
│   │   └── worker.py                        # ARQ worker entrypoint — imports orchestrator, not individual modules
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                                # Next.js (already scaffolded)
│   └── app/
│       ├── page.tsx                         # upload
│       ├── results/[id]/page.tsx            # axis cards + heatmap + explanation
│       └── analytics/page.tsx               # Module 8 eval reports
│
├── data/
│   ├── reference_media/                     # seed set for Module 5
│   └── eval_sets/                           # labeled sets for Module 8
│
└── docker-compose.yml                       # backend, frontend, redis (queue only) — Supabase is remote, no local DB container
```

Each `modules/<name>/contracts.py` is importable with no other module or the `orchestrator/`
package on the path — that's the enforced boundary from §6, not just a convention.

---

## 8. Open Decisions for the Team

These are genuine trade-offs, not settled by the docs above — flag them before building:

1. **ARQ vs. Celery for the queue.** Recommended ARQ (above) for simplicity; switch to Celery
   only if a GPU worker needs process-level isolation ARQ doesn't give.
2. **How much of Module 8 ships for the demo vs. after.** The eval harness is the right thing to
   build, but it's also the easiest to cut under time pressure — decide the minimum (even just
   Module 2 + Module 3 metrics) before the deadline, not during it.
3. **Whether logo/brand-impersonation detection (the marginal `logo.pt` asset) is in scope at
   all.** It's cheap to skip; only worth the fine-tuning pass if a judge/rubric explicitly asks
   for brand-impersonation detection.
4. **SerpApi reverse-image search: on or off for the demo.** It's the one component with a
   per-call external cost; decide the budget before wiring it in as a default path rather than a
   flag.
