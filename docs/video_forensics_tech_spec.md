# Video Deepfake Forensics Engine: Technical Specification

## 1. Module Overview & Scope
This module serves as the **Visual Forensics Sub-Engine** for our PS-2 Multi-Modal Misinformation Detection pipeline. 

It does not rely on a simple black-box CNN. To satisfy the hackathon's requirement for "robustness against unseen manipulation" (Deliverable 6) and "human-understandable evidence" (Deliverable 5), this engine analyzes `.mp4` files across three distinct dimensions:
* **Temporal:** Micro-jitter and unnatural landmarks over time.
* **Spectral (Frequency):** Grid artifacts left by generative AI upsampling.
* **Spatial:** Patch-level vision transformer anomalies.

**Dependencies to Install (Module Owner):**
`pip install opencv-python mediapipe torch torchvision transformers scipy numpy`

---

## 2. Core Architecture & Processing Pipeline

### Stage 1: Dense Snippet Extraction
Instead of reading 1,500 frames into RAM (which will crash our environment), we extract continuous temporal windows.
* **Logic:** Extract three 30-frame snippets (e.g., at 10%, 50%, and 90% of the video duration). 
* **Library:** `cv2.VideoCapture`

### Stage 2: 3D Facial Alignment & ROI Cropping
* **Logic:** Pass the snippets through MediaPipe to detect the face and map 468 3D landmarks.
* **Library:** `mediapipe.solutions.face_mesh`
* **Crucial Step:** We pad the bounding box by 15% to ensure we capture the jawline and neck blending seams, which is where face-swaps fail.

### Stage 3: Tri-Stream Forensic Processing
The cropped faces and landmarks are passed into three specialized algorithms (detailed in Section 3).

### Stage 4: Multi-Stream Fusion
* **Logic:** The results from the Temporal, Spectral, and Spatial streams are mathematically weighted (favoring the highest peak anomaly rather than a simple average).
* **Output:** A structured JSON dictionary passed to the Multimodal Aggregator.

---

## 3. The 3 Core Forensic Tasks (Implementation Details)

To the Video Module Owner: Focus your engineering time on these three algorithms rather than training a model from scratch.

### Task 1: Frequency Domain Forensics (Satisfies Deliverable 6)
Generative models (like Stable Diffusion or GANs) leave microscopic, high-frequency checkerboard artifacts when they upsample latent arrays into pixels. 
* **Implementation:**
  1. Convert the cropped face to grayscale.
  2. Apply a 2D Discrete Cosine Transform (`cv2.dct`).
  3. Shift the zero-frequency component to the center.
  4. Measure the variance in the high-frequency corners. Unnaturally high energy in the outer spectrum flags the image as synthetically generated or adversarially perturbed.

### Task 2: Landmark-Anchored Explainability (Satisfies Deliverable 5)
Judges need concrete text, not just percentages.
* **Implementation:**
  1. Run the padded face crop through a pre-trained Vision Transformer (e.g., Hugging Face `SiglipForImageClassification`).
  2. Extract the Attention Rollout (the spatial heatmap of where the model is looking).
  3. Intersect this heatmap with the MediaPipe landmarks. If the heatmap glows red over landmark 152, the code translates this to "lower chin boundary".
  4. **Output String:** "Highest synthetic visual anomaly localized at the lower chin boundary."

### Task 3: rPPG Biometric Pulse Extraction (Defeats "Unseen Manipulation")
Deepfakes are "biologically dead." Real videos contain micro-fluctuations in skin color corresponding to the human heartbeat.
* **Implementation:**
  1. Isolate the forehead using MediaPipe landmarks.
  2. Calculate the mean Green-channel pixel value across the 30-frame snippet.
  3. Apply a bandpass filter (`scipy.signal.butter`) between 0.7 Hz and 2.5 Hz (42–150 BPM).
  4. Run a Fast Fourier Transform (`np.fft.fft`). If no clear peak frequency exists, flag as synthetic.

---

## 4. The Data Contract (JSON Payload Schema)

**To the Teammates:** The Video Module will not output a simple string. When you call `analyze_video(path)`, it will return the following JSON schema. You must parse this to build the final report.

```json
{
  "modality": "video_deepfake_engine",
  "verdict": "FAKE",
  "confidence_score": 0.962,
  "forensic_streams": {
    "spatial_anomaly_score": 0.88,
    "spectral_artifact_detected": true,
    "biometric_pulse_detected": false
  },
  "adversarial_status": "HIGH-FREQUENCY PERTURBATION DETECTED",
  "flagged_segments_sec": [2.4, 6.8],
  "concrete_evidence": [
    "Biometric anomaly: Lack of remote photoplethysmography (blood volume pulse) detected across frames.",
    "Spectral anomaly: High-frequency 2D-DCT grid artifacts detected, indicating AI upsampling.",
    "Spatial anomaly: Patch-level inconsistencies observed along the left jawline blending boundary."
  ],
  "saliency_heatmap_path": "/tmp/attention_overlay_frame_82.jpg"
}
```

---

## 5. Multimodal Integration Workflow (How We Stitch It Together)

This is how the rest of the team will consume the Video Module's output to satisfy the Hackathon's 7 Mandatory Deliverables:

* **Handling Deliverable 1 & 2 (Cross-Modal Inconsistencies):**
  * **Audio Team:** You will extract the audio track. Compare your lip-sync (phoneme-to-viseme) timestamps with the `flagged_segments_sec` array from the video JSON. If the video engine flags a visual anomaly at 2.4s and the audio engine detects a lip-sync failure at 2.4s, we boost the total confidence score.
* **Handling Deliverable 3 (Out-of-Context Media Reuse):**
  * **Text/Context Team:** If the video engine returns `"verdict": "REAL"`, but the user-provided caption claims something else, you must use a Vision-Language Model (VLM) or NLP similarity check to prove the caption does not match the real video.
* **Handling Deliverable 5 (Explanation Generation - VERY IMPORTANT):**
  * **LLM / UI Team:** Do not prompt your LLM to "guess" why it's a deepfake. You will pass the `concrete_evidence` array directly into your LLM prompt. 
  * *Prompt Example:* "Using the following forensic forensic evidence points provided by our vision engine: {concrete_evidence}, write a 3-sentence non-technical explanation for the user."
  * **UI Team:** Surface the image located at `saliency_heatmap_path` on the frontend dashboard next to the text explanation so judges can physically see the bounding box.