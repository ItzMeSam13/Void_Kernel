# design.md: Nith Frontend UI Guide

> **For the coding agent (Antigravity):** Read this whole file before writing any UI code.
> Build the Nith frontend in the visual style described here. Follow the tokens, layout and component specs exactly. Where this file is silent, choose the option that is calmer, rounder and more spacious, never busier.

---

## 0. What we are building

**Nith** is a multimodal misinformation-verification tool. A user submits a claim with an image, video or audio, and gets back a report with **four independent findings**:

1. Claim veracity
2. Media authenticity
3. Cross-modal consistency
4. Historical reuse

The visual style comes from a "job board dashboard" reference: a **near-black rounded top bar**, a **soft light content sheet** with large rounded corners, **pastel color-blocked cards**, **outlined pill tags**, **black pill buttons**, and a **left filter column** with a dark promo card.

We reuse the *look*, not the content. There are no job listings, company logos or brand marks anywhere in this product.

### Stack (do not change without asking)
- Next.js (App Router, already scaffolded in `frontend/`), TypeScript
- Tailwind CSS with CSS variables for the tokens below
- `lucide-react` for icons (1.5px stroke, rounded caps)
- `next/font` for fonts
- No heavy UI kit. Build components by hand so the style stays consistent. Radix primitives (checkbox, slider, dropdown, dialog) are fine if restyled to this spec.

### Pages
| Route | Purpose | Reference analogue |
|---|---|---|
| `/` | Upload and check a claim, recent reports | Main "Recommended jobs" screen |
| `/results/[id]` | Four-axis report, heatmap, explanation, evidence | Expanded card / details view |
| `/analytics` | Module 8 eval reports (metrics, slices, latency) | Same shell, different grid |

---

## 1. Design principles

1. **Quiet confidence.** Lots of whitespace, few colors per screen, big rounded shapes.
2. **Color blocks carry meaning, but never alone.** Every status uses color **and** icon **and** text label (accessibility, and the product itself is about not over-claiming).
3. **Four findings, never one score.** The UI must never show a single combined "fake/real" number or badge.
4. **Honest states are first-class.** `inconclusive` and `not assessed` get the same visual dignity as a positive finding. Don't hide them or grey them into invisibility.
5. **Signals, not verdicts.** Wording on the UI says "signal detected", "no strong signal", "inconclusive", "not assessed". Never "FAKE!" or "100% real".
6. **Evidence is one tap away.** Every claim in the explanation links to the evidence behind it.

---

## 2. Design tokens

Define these as CSS variables in `app/globals.css` and map them in `tailwind.config.ts`. Never hardcode hex values in components.

### 2.1 Color

```css
:root {
  /* Page backdrop (the lavender-grey behind the main sheet) */
  --bg-backdrop:      #CBCEDC;
  --bg-backdrop-line: rgba(255,255,255,0.55);  /* thin decorative arcs/lines */

  /* App shell */
  --ink-900:  #0E0E10;   /* top bar, promo card, primary buttons */
  --ink-800:  #17171A;
  --ink-700:  #26262B;   /* hairlines on dark */
  --ink-500:  #6B6B75;   /* muted text on light */
  --ink-400:  #8E8E99;   /* labels, placeholders */
  --ink-200:  #E4E4EA;   /* borders on light */
  --ink-100:  #F1F1F5;
  --sheet:    #F8F8F6;   /* main content surface */
  --card:     #FFFFFF;   /* card outer shell */

  /* Text */
  --text-on-dark:        #FFFFFF;
  --text-on-dark-muted:  #9A9AA6;
  --text-on-light:       #111114;

  /* Accent */
  --accent-sky:   #7CC4F8;   /* slider handles, "Learn more" button, active dots */
  --accent-sky-600: #4AA8EE;

  /* Pastel card fills (inner colored panel) */
  --pastel-peach:    #FFE1CE;
  --pastel-mint:     #D6F5EA;
  --pastel-lavender: #E3DDF8;
  --pastel-sky:      #DDEFFC;
  --pastel-pink:     #F9DDEE;
  --pastel-grey:     #ECEDF5;

  /* Status (used only as small chips/dots/icons, plus the pastel panel tint) */
  --status-signal:       #E8667A;  /* signal detected / contradicted */
  --status-clear:        #2FAE8F;  /* no strong signal / supported */
  --status-inconclusive: #E0A23A;  /* inconclusive / uncertain */
  --status-na:           #8E8E99;  /* not assessed / unavailable */
}
```

Dark mode is **optional and low priority**. The reference is a light sheet with a dark header. If you add it later, only invert `--sheet` and `--card`, and keep the pastel panels unchanged.

### 2.2 Axis to pastel mapping (fixed, so users learn it)

| Axis | Pastel panel | Icon (lucide) |
|---|---|---|
| Claim veracity | `--pastel-peach` | `FileSearch` |
| Media authenticity | `--pastel-mint` | `ScanFace` |
| Cross-modal consistency | `--pastel-lavender` | `Link2` |
| Historical reuse | `--pastel-sky` | `History` |
| Supporting panels (eval, explanation, evidence) | `--pastel-pink` / `--pastel-grey` | as needed |

The pastel is the **axis identity**. The verdict is shown separately by a status chip (section 4.7). Don't tint the whole card red or green.

### 2.3 Typography

Use a geometric/humanist sans with a friendly, slightly rounded feel.

- **Display and headings:** `Manrope` (700/800), via `next/font/google`. Acceptable alternative: `Plus Jakarta Sans`.
- **Body and UI:** `Inter` (400/500/600).
- **Mono (hashes, scores, IDs):** `IBM Plex Mono` (400/500).

| Role | Size / line-height | Weight | Notes |
|---|---|---|---|
| Page title ("Recent checks") | 40/44 | 800 | letter-spacing -0.02em |
| Card title | 28/32 | 600 | max 2 lines, balanced wrapping (`text-wrap: balance`) |
| Section label | 15/20 | 500 | color `--ink-400` |
| Body | 15/22 | 400 | |
| Small / tag | 13/16 | 500 | |
| Micro / meta | 12/16 | 500 | |
| Nav | 17/24 | 500 | |

### 2.4 Radius, spacing, elevation

- **Radius scale:** `--r-sm: 12px`, `--r-md: 20px`, `--r-lg: 28px` (cards), `--r-xl: 40px` (the main sheet and app shell), `--r-pill: 999px`.
- **Spacing:** 4px base. Common steps: 8, 12, 16, 20, 24, 32, 40, 56.
- **Card gap:** 24px. **Sheet padding:** 56px horizontal, 48px top (reduce on small screens).
- **Shadows:** the sheet gets one soft large shadow: `0 30px 80px rgba(20,20,40,0.18)`. Cards have **no shadow**, only a 1px border `--ink-200`. Hover adds `translateY(-2px)` and a faint shadow `0 8px 24px rgba(20,20,40,0.08)`.
- **Borders:** 1px, `--ink-200` on light and `--ink-700` on dark.

---

## 3. Layout and shell

```
┌──────────────────────── page backdrop (--bg-backdrop + thin arcs) ────────────────────────┐
│  ┌────────────────────── app shell (radius 40, max-w 1720, centered) ──────────────────┐  │
│  │ TOP BAR (dark)    logo · nav · [location/lang] · avatar · settings · bell            │  │
│  │ ─────────────────────────────────────────────────────────────────────────────────── │  │
│  │ CLAIM BAR (dark)  [claim input ▾] [media type ▾] [language ▾] [view ▾]  [range ──●──●] │  │
│  ├──────────────────────────────────────────────────────────────────────────────────────┤  │
│  │ SHEET (light)                                                                         │  │
│  │  ┌ left col 320px ┐   Recent checks [386]                    Sort by: Last updated ⚙  │  │
│  │  │ promo card     │   ┌ card ┐ ┌ card ┐ ┌ card ┐                                       │  │
│  │  │ Filters …      │   └──────┘ └──────┘ └──────┘                                       │  │
│  │  └────────────────┘   ┌ card ┐ ┌ card ┐ ┌ card ┐                                       │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

- The app shell is a single rounded container (`--r-xl`, `overflow: hidden`) centered on the lavender backdrop with 64px margin on desktop.
- The **top bar and claim bar are one continuous dark block** (`--ink-900`), separated by a 1px `--ink-700` line. The sheet below it is light.
- The backdrop carries a few **thin white arc/circle line shapes** (SVG, 1px stroke, `--bg-backdrop-line`) partially cropped by the viewport edges. Purely decorative, `aria-hidden`, placed with `position: fixed; z-index: 0`.
- **Content grid:** `grid-template-columns: 320px 1fr; gap: 48px`. The card grid is 3 columns at >=1280px, 2 at >=820px, 1 below.
- A thin vertical hairline separates the filter column from the main column.

---

## 4. Components

### 4.1 Top bar
- Height 112px. Padding 0 56px.
- **Logo:** a small rounded-square glyph plus the wordmark "Nith" (Manrope 800, 26px, white). Make an original glyph, such as a stylized shield-check or magnifier-in-leaf. Do not copy the reference's logo.
- **Nav links:** `Check`, `Reports`, `Analytics`, `Docs`, `FAQ`. White at 100% when active, `--text-on-dark-muted` otherwise. The active link has a **2px white underline** (about 96px wide) sitting on the bar's bottom border, with 12px of padding between text and line.
- **Right cluster:** language selector (map-pin-style icon plus text, e.g. "English"), then three 48px circular icon buttons (avatar with a sky-blue notification dot, settings, bell). Circle buttons are 1px `--ink-700` outlined, transparent, with an icon of 20px `--text-on-dark`. Hover fills `--ink-800`.

### 4.2 Claim bar (the "search row")
Four fields plus one range control, in one row, separated by 1px vertical dividers (`--ink-700`, 40px tall).

Each field = **48px outlined circle icon** + label/value + small down-caret.
1. **Claim**: text input (placeholder "Paste a claim or caption"), search icon. Value text is white.
2. **Media type**: Image / Video / Audio / Text only.
3. **Language**: Auto-detect, English, Hindi, Marathi, and so on.
4. **Sort/View**: Latest / Highest uncertainty / Needs review.
5. **Range control** (right side): label "Confidence range" with the value "20% – 90%" right-aligned in white, above a **2px track** (`--ink-700` base, `--accent-sky` fill between the handles) with 20px round sky-blue handles (a subtle white 2px ring on focus). This filters the report list by confidence.

Placeholder/unselected values use `--text-on-dark-muted`. Selected values are white. On narrow screens, collapse into a horizontally scrollable row or an accordion.

### 4.3 Left column
**Promo card**
- Radius `--r-lg`, background `--ink-900`, with a **subtle noise texture** and **thin white arc line art** (1px, 18% opacity) behind the text.
- Heading: "Verify before you forward." Manrope 800, 34px, white, left-aligned, max 3 lines.
- CTA: full-width pill button, background `--accent-sky`, text `--ink-900`, 600 weight, 56px tall, label "Learn how it works".

**Filters**
- Heading "Filters" (Manrope 700, 28px) with a small black triangle collapse toggle on the right.
- Group labels ("Modality", "Verdict state", "Source") in `--ink-400`, 16px, with 24px space above.
- **Checkbox rows:** 24px rounded-square (radius 7px). Checked = filled `--ink-900` with a white check. Unchecked = 1.5px `--ink-200` outline. Label 17px `--text-on-light`. Row height 42px.
- Suggested groups:
  - *Modality:* Image, Video, Audio, Text only
  - *Verdict state:* Signal detected, No strong signal, Inconclusive, Not assessed
  - *Evidence:* Has source match, Echo-chamber warning, Recompression caveat

### 4.4 Section header
- Left: "Recent checks" (40px, 800) followed by a **count pill**: outlined 1px `--ink-200`, radius pill, 22px text, padding 8x20.
- Right: "Sort by:" in `--ink-400`, the current value in `--text-on-light` 500, then a small sliders icon button.

### 4.5 Report card (the main repeated unit)
Structure is a **white outer shell containing a pastel inner panel, plus a footer row**.

```
┌ outer: white, radius 28, 1px --ink-200, padding 8 ──────────────┐
│ ┌ inner: pastel fill, radius 24, padding 20 ─────────────────┐ │
│ │ [ 20 May, 2026 ]                                  (⚑)      │ │
│ │                                                            │ │
│ │ Media authenticity                                (icon)   │ │
│ │ Image · "Flood in City X"            ← title 28px          │ │
│ │                                                            │ │
│ │ ( Smaug 0.42 ) ( ManTraNet clear ) ( OCR: Hindi )          │ │
│ │ ( Recompressed )                                           │ │
│ └────────────────────────────────────────────────────────────┘ │
│  [● Inconclusive]  conf 0.64            [   Details   ]        │
└──────────────────────────────────────────────────────────────────┘
```

- **Date chip:** white pill, 14px text 500, padding 10x16, top-left of the inner panel.
- **Bookmark button:** 44px white circle, top-right, outlined bookmark icon. Filled black icon when saved. Used for "save / flag for review".
- **Small label:** the axis or media label, 15px 500, `--text-on-light` at 80%.
- **Title:** 28px/32 weight 600, max 2 lines.
- **Round icon badge** (right of title, 48px circle): the axis icon in white on `--ink-900`, or the **status icon** (see 4.7). It replaces the company logo in the reference. **No real brand logos.**
- **Tag pills:** 1px `--ink-900` at 35% opacity outline, transparent fill, radius pill, padding 8x14, 13px 500. They hold the signals ("Smaug 0.42", "Echo-chamber x0.75", "Hamming d=3"). Wrap to multiple lines, 8px gap.
- **Footer (outside the pastel panel, inside the white shell):**
  - Left: a **status chip** (4.7) plus confidence in mono (`conf 0.64`), and below it a muted line (e.g. "Telegram · Hindi" or the report ID).
  - Right: **Details** button, black pill, white text, 600, 52px tall, padding 0 32px. Hover `--ink-800`, press scale 0.98.
- Cards animate in with a 200ms fade-and-rise, staggered by 30ms.

### 4.6 The four-axis report layout (`/results/[id]`)
- Top: a header block with the submitted media thumbnail (radius 20), the claim text, the report ID in mono, and the timestamp.
- **Four axis cards in a 2x2 (desktop) or 1-column (mobile) grid**, using 4.5 with the axis pastel mapping from 2.2. Each card shows: the axis name, a status chip, confidence, the 2 to 4 strongest evidence tags, and a "Details" button that opens a right-hand drawer.
- Below: **Explanation panel** (`--pastel-grey`), 3 to 4 sentences. Every sentence that cites evidence has a small superscript marker; hovering or tapping it highlights the matching evidence row. The panel footer has a quiet "Wording checked against evidence" indicator when the bias regulator ran.
- Below that: **Evidence list** (white cards): source domain, date, stance chip (supports / contradicts / neutral), a snippet, and an external-link icon. Show an "Echo-chamber warning" banner (`--pastel-peach`) when applicable.
- Where available, a **heatmap overlay** card shows the image with an adjustable opacity slider (default 40%) and a toggle for the original. For video, show a **timeline strip** with flagged timestamps as small markers.
- **Never** render a combined verdict, a single gauge for "overall fakeness", or a red/green banner over the whole report.

### 4.7 Status chips and states

A chip is a pill with a 8px dot (or icon), label text and a tinted background (`status color` at 14% opacity, text in a darker shade of the same hue).

| State | Label | Icon | Color |
|---|---|---|---|
| Signal detected / contradicted | "Signal detected" | `AlertTriangle` | `--status-signal` |
| No strong signal / supported | "No strong signal" | `CheckCircle2` | `--status-clear` |
| Inconclusive / uncertain | "Inconclusive" | `HelpCircle` | `--status-inconclusive` |
| Not assessed | "Not assessed" | `MinusCircle` | `--status-na` |
| Running | "Checking…" | spinner | `--accent-sky` |
| Queued | "In queue" | `Clock` | `--ink-400` |

Rules:
- Always show the text label. Never rely on color alone.
- `Not assessed` appears as a real card or row with an optional reason line ("Audio too short"). Never leave an empty gap.
- When a **confidence modifier** is active (e.g. recompression), show a small tag: "Confidence reduced: recompression".

### 4.8 Buttons
- **Primary:** black pill (`--ink-900`), white text, 52px tall.
- **Accent:** sky pill (`--accent-sky`), dark text, used in the promo card and the main "Check this" call-to-action on the upload page.
- **Secondary:** transparent with a 1px `--ink-200` outline, pill.
- **Icon button:** 44 to 48px circle, outlined.
- Focus: a 2px outer ring in `--accent-sky-600` with a 2px offset. Disabled: 40% opacity, no hover.

### 4.9 Upload page (`/`)
- Keep the same shell. The claim bar drives the input. Below it, in the main column, show a large **drop zone card**: `--pastel-sky` fill, radius `--r-lg`, dashed 1.5px border in `--ink-900` at 30%, a central 64px circular icon, the text "Drop an image, video or voice note", and an accent "Choose file" pill button.
- File validation messages appear as small inline chips (e.g. "File too large (max 20 MB)").
- After submit, route to `/results/[id]`, where cards show **skeleton states** while jobs run. Each axis card moves independently from "Checking…" to its final state, so the user sees progress. Poll `GET /api/v1/results/{job_id}`.
- Below the drop zone, show "Recent checks" cards (section 4.5).

### 4.10 Analytics page (`/analytics`)
Same shell and card style, with metric cards in the pastel panels:
- Per module: precision, recall, FPR, latency p50/p95. Always show **n** and the **95% interval** next to each number ("FPR 7.1% (4–13%), n=140").
- Slice table (language, bitrate, compression) in a white card with row hover `--ink-100`.
- A risk-versus-coverage chart. Use Recharts or visx with a minimal style: 2px lines, no gridlines except a faint baseline, labels in `--ink-500`.
- Label any simulated or seeded data clearly with a visible "Demo data" chip. Never present simulated numbers as real usage.
- Data from `GET /api/v1/eval/{module}`.

### 4.11 Empty, loading, error
- **Loading:** shimmer skeleton in the same shapes (pastel panel plus pill shapes), 1.4s loop, subtle.
- **Empty:** a centered illustration made of simple geometric line art (circles and arcs, matching the backdrop) with a one-line message and a pill CTA.
- **Error:** a `--pastel-peach` card with a clear message and a "Try again" secondary button. Never expose stack traces.

---

## 5. Motion

- Durations 150 to 250ms, easing `cubic-bezier(0.2, 0.8, 0.2, 1)`.
- Hover: cards lift 2px. Buttons darken. Icon buttons fill.
- Drawer: slide from the right over 250ms with a 45% black overlay.
- Slider handles scale 1.1 on drag.
- Respect `prefers-reduced-motion: reduce`: remove transforms and staggered animations, keep opacity fades.

---

## 6. Responsive behavior

| Breakpoint | Behavior |
|---|---|
| >=1280px | Full layout: 320px left column plus 3-column card grid |
| 820 to 1279px | Left column collapses into a "Filters" button that opens a drawer. 2-column grid |
| <820px | Single column. Top bar collapses to logo plus hamburger. Claim bar becomes a stacked form. Sheet radius reduced to 28px. Padding 20px |

On mobile the app shell goes edge to edge (no backdrop margin) but keeps the rounded top corners.

---

## 7. Accessibility

- Text contrast: at least 4.5:1. Check muted text on pastel panels. `--text-on-light` is the minimum for text on pastels.
- All interactive elements are keyboard reachable with a visible focus ring.
- Checkboxes, sliders and dropdowns use proper roles and labels (use Radix or native elements).
- Status is conveyed by text plus icon, never color alone.
- The heatmap and timeline need text alternatives ("Highest anomaly near the lower left of the image").
- Touch targets are at least 44x44px.
- Set `lang` on the page, and support Indian scripts. Make sure the font stack falls back to `Noto Sans Devanagari` and similar, so Hindi and Marathi text renders properly.

---

## 8. Content and copy rules

- Use **hedged, evidence-based wording**: "No supporting sources were found", "One detector signal was raised". Avoid "proves", "obviously", "definitely fake".
- Show confidence as a number plus the state label. Confidence is not accuracy, so add a tooltip: "How strongly the available evidence agrees. It is not a guarantee."
- Include a persistent footer note: "Results are evidence signals, not proof."
- Plain language first, jargon behind a "Technical details" toggle (model names, versions, raw scores).
- Dates shown as `20 May, 2026`. Scores in mono with fixed decimals.

---

## 9. Suggested file structure

```
frontend/
├── DESIGN.md                      # this file
├── app/
│   ├── layout.tsx                 # fonts, backdrop, app shell
│   ├── globals.css                # tokens (section 2)
│   ├── page.tsx                   # upload + recent checks
│   ├── results/[id]/page.tsx      # four-axis report
│   └── analytics/page.tsx
├── components/
│   ├── shell/    TopBar.tsx  ClaimBar.tsx  Backdrop.tsx  AppShell.tsx
│   ├── filters/  PromoCard.tsx  FilterGroup.tsx  CheckboxRow.tsx
│   ├── cards/    ReportCard.tsx  AxisCard.tsx  MetricCard.tsx  EvidenceRow.tsx
│   ├── ui/       Button.tsx  Pill.tsx  StatusChip.tsx  RangeSlider.tsx  Drawer.tsx  Skeleton.tsx
│   └── report/   ExplanationPanel.tsx  HeatmapViewer.tsx  VideoTimeline.tsx
└── lib/
    ├── api.ts                     # typed client for /api/v1/*
    └── types.ts                   # mirrors backend Pydantic contracts (4 axes, NotAssessed)
```

`lib/types.ts` must model each finding as a **tagged union** (`status: "ok" | "not_assessed"`), so the UI can never show a score for something that wasn't assessed.

---

## 10. Do and don't

**Do**
- Use big radii, generous padding and pastel panels inside white card shells.
- Keep the dark top block and light sheet contrast.
- Show `inconclusive` and `not assessed` as normal, designed states.
- Use original icons and logos.

**Don't**
- Don't use real brand logos or names (no Amazon, Google, Twitter, etc.) in cards or sample data. Use generic placeholders.
- Don't show a single combined fake/real score, gauge or banner.
- Don't use red or green as full-card backgrounds.
- Don't add gradients, glassmorphism, heavy shadows or neon. The reference is flat, soft and calm.
- Don't use more than one pastel plus the black and sky accents in a single card.
- Don't fabricate usage statistics. Demo data must be labeled.

---

## 11. Acceptance checklist

- [ ] The page matches the reference's structure: dark top bar, claim bar with range slider, rounded light sheet, left promo plus filters, 3-column pastel card grid.
- [ ] All colors, radii and fonts come from tokens, with no stray hex values.
- [ ] The four axes have fixed pastel colors and icons, and no combined verdict appears anywhere.
- [ ] Every status shows a color, an icon and a text label.
- [ ] `not_assessed` renders as a real state with a reason.
- [ ] Layout works at 1440, 1024 and 390px widths.
- [ ] Keyboard navigation and focus rings work throughout.
- [ ] Indian-language text renders correctly.
- [ ] Reduced-motion preference is respected.
- [ ] Skeleton, empty and error states exist for every data view.
- [ ] Simulated data is labeled "Demo data".