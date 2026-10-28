# Multimodal Misinformation Detection — Models, APIs, and Module Plan

This guide describes a modular system for verifying claims associated with images and videos. It separates factual claim verification, cross-modal consistency, AI-generated media detection, image manipulation detection, and historical media reuse.

The existing **SecureVox** project is treated as a reference for relevant audio-analysis techniques and models. Only the audio components relevant to this project are included: speech transcription and synthetic-audio/deepfake detection. Speaker matching, age/gender estimation, and comparing two speakers are out of scope.

> **Important:** Model outputs are evidence signals, not definitive proof. A real image can be used with a false caption, AI-generated media can accompany a true claim, and a genuine image can be reused out of context. Keep these findings separate in the final report.

---

# 1. Module A — Image + Text Verification

The input may be a text claim with an image, an image containing text, or an image without a caption. The system investigates the factual claim, image content, authenticity signals, and historical reuse separately.

## A1. Image description

- **Model:** [`Salesforce/blip-image-captioning-base`](https://huggingface.co/Salesforce/blip-image-captioning-base)
- **Purpose:** Generate a textual description of visible content, such as a flooded street, damaged building, or group of people.
- **Integration:** Load through Hugging Face Transformers and run locally. A LangChain `ImageCaptionLoader` exists in the older `langchain-community` package, but for a new project, direct Transformers inference is the safer foundation.
- **Cost/licence:** The model card lists BSD-3-Clause. Running it locally has no per-request API charge, although compute resources are still required.

## A2. Claim-to-image matching

- **Model:** [`openai/clip-vit-base-patch32`](https://huggingface.co/openai/clip-vit-base-patch32)
- **Purpose:** Calculate image-text similarity to estimate whether a claim is semantically compatible with an image.
- **Difference from BLIP:** BLIP describes the scene; CLIP compares the image with supplied text or candidate descriptions.
- **Integration:** Use Hugging Face Transformers directly. No separate LangChain image-text similarity adapter is required.
- **Cost/licence:** Model weights can be downloaded and run locally. Review the model card and evaluate it on your own data before relying on it. Similarity is not a probability that the claim is true.

## A3. Embedded-text extraction

- **Tool/model:** [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- **Purpose:** Extract text from memes, screenshots, posters, and news graphics so claims written inside the image can be fact-checked.
- **Integration:** Native Python API; no LangChain adapter is needed.
- **Cost/licence:** Apache-2.0 open-source toolkit, runnable locally.

## A4. AI-generated image detection

- **Model candidate:** [`abacusai/Smaug-AI-Image-Detector`](https://huggingface.co/abacusai/Smaug-AI-Image-Detector)
- **Purpose:** Estimate whether an image may be AI-generated. This is separate from checking whether its caption is true.
- **Integration:** Use the model's native Python inference implementation.
- **Cost/licence:** The model card lists Apache-2.0 and supports local inference. New generators and AI-edited regions may evade detection, so treat the score as a signal rather than proof.

## A5. Image manipulation detection

- **Model:** A suitable manipulation-localization model from the existing `document_forgery` project, provided testing shows that it works on natural photographs.
- **Purpose:** Look for evidence of editing, splicing, or copy-move manipulation.
- **Integration:** Use the model's native inference function and validate its outputs on a labeled set of natural images.
- **Cost:** No per-call API fee if run locally with available weights. Do not assume a detector trained or used on documents will generalize to ordinary photographs.

## A6. Historical image reuse

### MVP: local image matching

- **Tools:** SHA-256, perceptual hashing (pHash), and a reference-image database.
- **Purpose:** SHA-256 identifies identical file contents; pHash helps find visually similar images in the collection.
- **Integration:** Local Python hashing plus a reference store containing hashes, known source URLs, dates, and captions.
- **Cost:** Local hashing is free and does not need a model API.

### Optional extension: public-web reverse-image search

- **Service:** [SerpApi Google Lens API](https://serpapi.com/google-lens-api)
- **Purpose:** Find external visual matches and associated web-result details.
- **Integration:** Separate HTTP/API client; this is not a LangChain model integration.
- **Cost:** SerpApi has free and paid plans; check current limits and pricing before relying on it in the demo.

A hash does not discover the origin of an image by itself. You need a reference collection or a separate reverse-image search service. Finding an older match is evidence of possible reuse, not proof that the current claim is false.

## A7. Image module: questions and evidence

| Question | Evidence/component |
|---|---|
| What is visible in the image? | BLIP image caption |
| Does the supplied caption match the image? | CLIP similarity and visual description |
| What factual assertions are written inside the image? | PaddleOCR |
| Is the image potentially AI-generated? | Smaug detector signal |
| Is the image potentially manipulated? | Validated image-forensics detector |
| Has the image appeared in an older story? | pHash/reference database and reverse-image results |
| Is the associated factual claim true? | Internet evidence and claim-verification module |

---

# 2. Module B — Video Verification

Video analysis includes visual frames, spoken claims, audio authenticity, and possible historical reuse. The image modules can be reused on selected video frames.

## B1. Video preprocessing and frame extraction

- **Tools:** [FFmpeg](https://ffmpeg.org/), [OpenCV](https://opencv.org/), and optionally [PySceneDetect](https://www.scenedetect.com/).
- **Purpose:** Extract representative frames with timestamps, separate the audio track, and collect basic metadata such as duration and frame rate.
- **Integration:** Native Python tools called from the backend or a LangGraph node.
- **Cost:** Free local processing. Processing time depends on video length, resolution, and frame-sampling strategy.

## B2. Frame-level image analysis

Run applicable image modules on selected frames and preserve the timestamp for every result.

| Model/tool | Role for video frames |
|---|---|
| BLIP | Describe each selected frame |
| CLIP | Compare the claim with the frame's visual content |
| PaddleOCR | Extract text visible in the frame |
| Smaug | Estimate synthetic-image signals for individual frames |
| Image-manipulation model | Check for supported manipulation indicators |
| pHash + reverse-image search | Find visual matches to older images or stories |

Do not automatically label an entire video fake because one frame is suspicious. Report which timestamp was analyzed and what the model found.

## B3. Audio extraction

- **Tool:** FFmpeg.
- **Purpose:** Extract the video's audio stream and convert it to the format required by transcription and detection models, such as mono 16 kHz WAV when supported.
- **Integration:** Native command-line/Python integration; no LangChain adapter is needed.
- **Cost:** Free local processing.

This is preprocessing, not a deepfake detector.

## B4. Speech transcription and claim extraction

- **Model:** [OpenAI Whisper `small`](https://huggingface.co/openai/whisper-small), or [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for optimized local inference.
- **Purpose:** Transcribe spoken audio so the application can extract factual claims and send them to the same fact-checking module used for image + text.
- **Integration:** Run Whisper locally using its Python implementation or Transformers. Use a native processing function rather than requiring a LangChain transcription wrapper.
- **Cost/licence:** The Whisper project is MIT-licensed; local inference has no per-minute API charge. Compute resources are still required.

A language model may organize the transcript into concise claims, but it should not be treated as the source of truth about what happened.

## B5. AI-generated / deepfake audio detection

This is the main audio-forensics component relevant to this project. Speaker identity matching, age/gender estimation, and comparison of two speakers are out of scope.

### First candidate: SecureVox Wav2Vec2 model

- **Model:** [`mo-thecreator/Deepfake-audio-detection`](https://huggingface.co/mo-thecreator/Deepfake-audio-detection)
- **Architecture:** Fine-tuned Wav2Vec2 audio-classification model.
- **Purpose:** Estimate whether extracted speech audio resembles real or synthetic speech.
- **Integration:** Use Transformers' native audio-classification code and evaluate the checkpoint on the expected real/synthetic audio domain.
- **Cost/licence:** The model card lists Apache-2.0. Downloadable weights and local inference are available without a per-request inference API charge. Review the model's dataset and intended-use limitations; do not rely solely on advertised evaluation accuracy.

### Alternative candidate: AASIST

- **Model/implementation:** [AASIST — Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks](https://github.com/clovaai/aasist)
- **Purpose:** Analyze speech for bona fide versus spoofed-audio signals using spectral and temporal features.
- **Integration:** Use its native inference code and pretrained checkpoint.
- **Cost/licence:** The referenced implementation is MIT-licensed. Performance can vary between datasets, so benchmark before deployment.

**Recommendation:** Start by evaluating the SecureVox Wav2Vec2 model because it is directly relevant to the previous project. Benchmark AASIST only if time and labeled test data are available; both models are not required for the MVP.

Use result labels such as `synthetic_audio_signal_detected`, `no_strong_signal_detected`, or `inconclusive`. Do not claim that a voice is definitively genuine or fake based on one detector.

## B6. Optional audio/video synchronization check

- **Model candidate:** [SyncNet reference implementation](https://github.com/joonson/syncnet_python)
- **Purpose:** Estimate whether spoken audio and visible mouth movements are temporally aligned. This can help investigate possible dubbing or audiovisual manipulation.
- **Integration:** Native model inference as a separate step after audio and frame extraction.
- **Cost/licence:** Public research implementation; review its exact licence and dependencies before deployment.

This is different from voice deepfake detection: the audio classifier analyzes the audio signal, while synchronization analysis examines the relationship between the audio and video.

## B7. Historical video reuse

Use timestamped keyframes from B1 and apply the historical image-matching module:

1. Select representative keyframes.
2. Compare them against the local pHash/reference-image database.
3. Search selected frames using a reverse-image service if available.
4. Collect source URLs, publication dates, and event descriptions.
5. Compare those sources against the video's spoken claim and caption.

A whole-video file hash alone is inadequate because reposted videos may be cropped, edited, or re-encoded.

---

# 3. Module C — Shared Fact-Checking and Reasoning Engine

This module is used by both image + text and video. The existing Tavily integration should be reused rather than duplicating general web search.

## C1. Internet claim verification

- **Integration:** Existing Tavily search implementation.
- **Purpose:** Search for the submitted claim, retrieve relevant web pages, and collect supporting or contradicting evidence. For video, claims come from the spoken transcript; for images, they come from the supplied caption or OCR text.
- **LangChain option:** [`langchain-tavily`](https://python.langchain.com/docs/integrations/tools/tavily_search/) provides Tavily search/extraction tools. The existing function can also be called directly.
- **Cost:** Tavily offers plans with free allowances and paid usage. Check current plan limits and credit usage before the demo.

Finding a claim online means it has been published; it does not prove that it is true.

## C2. Existing fact-check database search

- **Optional API:** [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api/reference/rest)
- **Purpose:** Search previously fact-checked claims by text and use its image-search endpoint where applicable.
- **Integration:** Direct API client; it is supplementary to Tavily.
- **Cost:** Requires an API key. Confirm quota, access, and billing settings before depending on it.

The image-search endpoint is not an unrestricted reverse-image search of the whole internet.

## C3. Claim-versus-evidence comparison

- **Model:** [`cross-encoder/nli-deberta-v3-base`](https://huggingface.co/cross-encoder/nli-deberta-v3-base)
- **Purpose:** Compare a claim with a retrieved passage and estimate whether the passage supports it, contradicts it, or is neutral.
- **Integration:** Run locally using Sentence Transformers. LangGraph can call it as an ordinary Python function.
- **Cost/licence:** The checkpoint is Apache-2.0 and can be run locally.

NLI is not a fact database: it needs relevant source passages. Validate its predictions and do not use one unrelated passage to declare a claim false.

## C4. Final evidence aggregation and explanation

The reasoning layer combines:

- Web evidence and existing fact-checks.
- Claim-to-image or claim-to-video consistency.
- Synthetic-image and synthetic-audio signals.
- Image manipulation indicators.
- Historical media matches.
- Audio/video synchronization findings, when available.

It should produce separate findings for claim veracity, media authenticity, cross-modal consistency, and historical reuse, then generate an overall assessment consistent with the evidence.

- **Recommended orchestration:** [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview), which can coordinate independent processing steps and conditional branches.
- **Optional explanation model:** Gemini via [`langchain-google-genai`](https://python.langchain.com/docs/integrations/chat/google_generative_ai/). Use it to turn validated evidence into readable explanations, not as the sole authority on whether content is true.
- **Integration principle:** Use ordinary Python functions for local model inference. Not every model needs a LangChain adapter.

---

# 4. Final Stack — MVP Recommendation

| Module | Recommended model/tool | Integration approach | Local/free status |
|---|---|---|---|
| Image captioning | BLIP base | Direct Transformers; legacy `ImageCaptionLoader` exists | Local inference; BSD-3-Clause model card |
| Claim-image similarity | CLIP ViT-B/32 | Direct Transformers | Local inference available; evaluate limitations |
| Text in images | PaddleOCR | Native Python | Apache-2.0 |
| AI-generated image detection | Smaug AI Image Detector | Native Python inference | Apache-2.0 |
| Image manipulation | Validated `document_forgery` detector | Existing native implementation | No per-call API fee with local weights |
| Historical image reuse | pHash/SHA-256 + optional reverse-image API | Python hashing/API client | Local matching free; reverse search may cost |
| Video frames/audio | FFmpeg + OpenCV; optional PySceneDetect | Direct Python | Free local processing |
| Speech transcription | Whisper small / faster-whisper | Native inference | Local inference; no per-minute API fee |
| AI-generated audio | SecureVox Wav2Vec2 detector | Direct Transformers | Apache-2.0 model card; local inference |
| Alternative audio detector | AASIST | Native inference | MIT-licensed implementation |
| Audio/video synchronization | SyncNet | Native inference | Public research code; review licence |
| Internet evidence | Tavily | Existing integration or `langchain-tavily` | Free allowance and paid usage limits |
| Fact-check database | Google Fact Check Tools API | Direct API client | API key; check quota/billing |
| Claim/evidence comparison | DeBERTa NLI | Sentence Transformers | Apache-2.0 |
| Workflow orchestration | LangGraph | Native LangGraph nodes | Open source |
| Explanation generation | Optional Gemini | `langchain-google-genai` | API free tier/limits vary |

---

# 5. Build Order

## Phase 1 — Image + Text

Build BLIP, CLIP, OCR, a synthetic-image detector, pHash-based historical matching, and integration with Tavily. Add manipulation forensics if the existing detector works on natural images.

## Phase 2 — Video

Extract timestamped frames and audio. Reuse the image pipeline on frames, use Whisper for the transcript, and the SecureVox Wav2Vec2 detector for synthetic-audio signals. Add historical keyframe matching.

## Phase 3 — Reasoning and validation

Combine Tavily's source evidence, model results, and historical matches. Add DeBERTa NLI, a LangGraph workflow, a structured evidence report, and evaluation on labeled examples.

---

# 6. Important Design Rules

1. **False claim, AI-generated media, manipulated media, and old media reused out of context are different findings.** Investigate each independently.
2. **Similarity is not truth.** CLIP similarity and image captions do not prove that a claim is factually correct.
3. **Historical matching needs source context.** pHash only finds matches in the database you have indexed; reverse-image search results still require date/event verification.
4. **Audio anomalies are not proof of deepfakes.** Spectral and noise-floor differences can result from ordinary recording, compression, or editing.
5. **Keep evidence traceable.** Record source URLs, publication dates, model versions, outputs, and limitations.
6. **Treat unavailable checks honestly.** If a model/API fails or a modality was not analyzed, mark it as unavailable/not assessed rather than inventing a score.
7. **Evaluate before trusting.** Build a labeled test set and measure false positives/negatives. Use detector scores as signals, not universal probabilities.

The goal is a multimodal verification system that combines independent evidence and explains its conclusions, rather than a single model that labels everything simply as fake or real.
