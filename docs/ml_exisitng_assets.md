# Asset Reuse Audit — document_forgery → PS 2 (Multi-Modal Misinformation Detection)

Audit of every model weight currently on disk in `document_forgery`, checked against **PS 2: Multi-Modal Misinformation Detection with Explanation Generation**, sorted by how much work stands between it and being useful there.

**Weights found:** 13 files, ~1.0 GB (all under `doc_forg_wts/`)

**Scorecard:** 3 reuse as-is · 3 need fine-tuning · 5 missing (train new) · 8 dead weight (discard)

---

## 1. Reuse as-is

Nothing here was ever fine-tuned on documents specifically — they're generic pipelines or zero-shot forensic backbones, so they carry over to natural images/video with no retraining.

### ManTraNet / BusterNet-style forensic pipeline
- **What:** VGG16 (anomaly stream) + ResNet50 (copy-move stream), run **zero-shot** — never fine-tuned on documents.
- **Why it transfers:** Directly detects splicing and copy-move artifacts in any photo, which is most of what "manipulated image" means for a misinfo pipeline.
- **Source:** `member2_spatial_forensics.py`
- **Covers PS deliverable:** #4 (synthetic/manipulated media)

### SHA-256 + pHash fingerprinting
- **What:** Exact-match hash plus DCT perceptual hash with Hamming-distance tiers (<5 same, 5–15 modified, >15 different).
- **Why it transfers:** This *is* out-of-context reuse detection — compare incoming media against a reference store and you're done.
- **Source:** ingestion / blockchain module
- **Covers PS deliverable:** #3 (out-of-context media reuse)

### Gemini semantic-validation integration
- **What:** Existing "does this text make sense" API call pattern.
- **Why it transfers:** Gemini is multimodal, so the same call extends to "does this caption match this image" and to writing the final evidence-citing explanation.
- **Source:** `text_forensics_engine.py`
- **Covers PS deliverables:** #2 (caption/media mismatch), #5 (explanation generation)

---

## 2. Needs fine-tuning

The *backbone* is generic and worth keeping as initialization — it saves a pretraining pass. The *head* sitting on top of each one is trained for a document-specific output and has to be thrown away and retrained on the new task.

### `swin_base_backbone.safetensors` (438 MB)
- **What:** Swin-Transformer backbone the DTD tamper model was built on.
- **Action:** Keep the backbone as a strong initializer for a new *natural-image* manipulation-localization head. Discard `dtd_model.pth`'s head — it only knows "tampered document pixel," not "manipulated photo pixel."
- **Covers PS deliverable:** #4 (after retraining)

### `efficientnet_b0_backbone.safetensors` (21.4 MB)
- **What:** EfficientNet-B0 backbone the font classifier was built on.
- **Action:** Reasonable starting point for a lightweight deepfake/GAN-artifact image classifier head. Discard `font_classifier.pth`'s head — it's useless outside documents.
- **Covers PS deliverable:** #4 (after retraining)

### `logo.pt` (YOLOv8s logo detector, 22.5 MB) — marginal
- **What:** YOLO logo/letterhead detector.
- **Action:** Only worth touching if "out-of-context reuse" is scoped to include brand/logo impersonation. Built for letterheads, not memes or social screenshots — fine-tune on a social-media logo dataset before trusting it, or skip it. Lowest priority in this section.

---

## 3. Missing — must be trained from scratch

Nothing in the current stack does these jobs, even partially. This is the actual build list for the new project.

| Gap | What's needed | Covers PS deliverable |
|---|---|---|
| **Image deepfake / GAN-artifact detector** | Face-swap and diffusion-generated image detection (e.g. fine-tune on FaceForensics++ / DFDC, or a frequency-artifact detector). No equivalent exists — the current forensic stack catches splicing/copy-move, not synthetic generation. | #4 |
| **Video deepfake detector** | Temporal/frame-consistency or lip-sync model. The entire current pipeline is single-image or document-page based — zero video capability exists anywhere in the codebase. | #1, #4 |
| **Cross-modal embedding model (CLIP or similar)** | A dedicated image-caption similarity score. Gemini can approximate this qualitatively, but the quantitative evaluation deliverable almost certainly expects a measurable embedding-distance metric, not just an LLM opinion. | #2, #7 |
| **Adversarial robustness layer** | Nothing in document_forgery was ever tested against adversarial perturbation (compression, re-encoding, pixel-level attacks). Needs its own evaluation harness and likely adversarial training/augmentation pass. | #6 |
| **Quantitative evaluation harness** | Accuracy, robustness, and explanation-quality metrics end-to-end. The old project only ever reported ad-hoc scores in a validation report — there's no reusable benchmark/eval code to inherit. | #7 |

---

## 4. Dead weight — discard, don't port

Document-specific fine-tuned weights with no equivalent concept in misinformation detection. Not worth carrying over even as inspiration.

- `signature.pt`, `stamp.pt`, `handwriting.pt` — YOLO specialists for document elements
- `app/backend/ml/runs/yolov8_roi_detection/weights/best.pt` / `last.pt` — custom 5-class ROI detector (signature/stamp/handwriting/logo)
- `dtd_model.pth`, `font_classifier.pth` — the fine-tuned *heads* (backbones above are kept)
- Signature Siamese network, Seal autoencoder — weights don't even exist anymore (deleted in a refactor), and the domain doesn't map here regardless

Stock pretrained checkpoints (`yolov8s.pt`, `yolo26n.pt`, `yolov8s-world.pt`) are generic enough to use as training starting points for any new YOLO-based detector, but carry no document-specific value either way.

---

## Bottom line

**Real head start:** media-reuse detection (#3) and part of explanation generation (#5) are close to done on day one — it's mostly wiring, not modeling.

**Real gap:** deepfake/synthetic-media detection (image *and* video, #4) and the quantitative cross-modal + robustness eval (#2, #6, #7) have to be built essentially from zero. That's where the hackathon time actually needs to go.
