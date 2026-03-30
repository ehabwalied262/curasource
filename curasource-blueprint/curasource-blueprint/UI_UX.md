# UI_UX.md — CuraSource Design System & User Experience

---

## Design Philosophy

CuraSource deals with medical and fitness information that people may act upon. The design must communicate **trust, precision, and clarity** above everything else. This is not a flashy product — it is a reliable reference tool.

**Core principles:**
1. **Trust is the product** — every design decision reinforces or erodes trust
2. **Citations are first-class** — not footnotes, not afterthoughts
3. **Clarity over cleverness** — medical information presented simply
4. **Progressive disclosure** — show the answer first, let users dig deeper
5. **Honest limitations** — design communicates what the system cannot do

---

## Visual Identity

### Color System
```css
:root {
  /* Primary — deep ink blue, conveys authority and precision */
  --color-primary-900: #0D1B2A;
  --color-primary-800: #1B2E45;
  --color-primary-700: #2A4260;
  --color-primary-500: #3D6B9E;
  --color-primary-300: #7AAFD4;
  --color-primary-100: #D6EAF5;

  /* Accent — warm amber, used sparingly for key actions */
  --color-accent-600: #D97706;
  --color-accent-400: #F59E0B;
  --color-accent-100: #FEF3C7;

  /* Semantic */
  --color-verified: #10B981;     /* Green — citation verified */
  --color-warning: #F59E0B;      /* Amber — low confidence */
  --color-error: #EF4444;        /* Red — failed verification */
  --color-neutral: #6B7280;      /* Gray — secondary text */

  /* Surface */
  --color-bg: #FAFAF9;           /* Off-white, warmer than pure white */
  --color-surface: #FFFFFF;
  --color-surface-raised: #F5F5F4;
  --color-border: #E7E5E4;
  --color-border-strong: #D6D3D1;
}

/* Dark mode */
[data-theme="dark"] {
  --color-bg: #0D1117;
  --color-surface: #161B22;
  --color-surface-raised: #1C2128;
  --color-border: #30363D;
  --color-primary-900: #E6EDF3;
}
```

### Typography
```css
/* Display — Fraunces (editorial, authoritative serif) */
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,400;0,600;1,300&display=swap');

/* Body — DM Sans (clean, readable, medical context appropriate) */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');

/* Monospace — JetBrains Mono (code, citations, IDs) */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'DM Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;

  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;
}
```

### Spacing
```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
}
```

---

## Layout Architecture

### Main App Layout
```
┌────────────────────────────────────────────────────────┐
│  SIDEBAR (280px)        │  MAIN CONTENT                │
│  ─────────────────────  │  ─────────────────────────── │
│  [Logo] CuraSource      │                              │
│                         │  [CHAT AREA or BROWSER]      │
│  [New Chat]             │                              │
│                         │                              │
│  Recent Sessions        │                              │
│  > What is STEMI?       │                              │
│  > Progressive overload │                              │
│  > Metformin in CKD     │                              │
│                         │                              │
│  ─────────────────────  │                              │
│  [Corpus Browser]       │                              │
│  [Settings]             │                              │
│  [User Account]         │                              │
└────────────────────────────────────────────────────────┘
```

### Chat Layout
```
┌──────────────────────────────────────────────────────┐
│  Domain Filter:  [🏥 Medical] [💪 Fitness] [🔀 Both] │
├──────────────────────────────────────────────────────┤
│                                                      │
│  [Message History — scrollable]                      │
│                                                      │
│  USER: What is first-line treatment for T2DM?        │
│                                                      │
│  CURASOURCE:                                         │
│  The first-line pharmacological treatment for        │
│  type 2 diabetes mellitus is metformin [1]✅,        │
│  unless contraindicated. In patients with CKD        │
│  stage 3b+, dose reduction is required [2]⚠️.        │
│                                                      │
│  ─── Sources ──────────────────────────────────────  │
│  [1]✅ Harrison's 21st Ed, Ch.396, p.2855            │
│       "Metformin is the preferred initial..."        │
│  [2]⚠️ Davidson's 24th Ed, Ch.21, p.712             │
│       "Renal impairment requires adjustment..."      │
│                                                      │
│  [👍] [👎]                                           │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [Ask anything about medicine or fitness...    ] [→] │
└──────────────────────────────────────────────────────┘
```

---

## Key Components

### ChatMessage
```tsx
interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;              // Markdown with inline citation markers [1]
  citations: Citation[];
  isStreaming?: boolean;
}

// Citation marker renders as clickable superscript
// [1] → <CitationBadge index={1} status="verified" onClick={openSourceViewer} />
```

### CitationBadge
```tsx
interface CitationBadgeProps {
  index: number;
  status: "verified" | "low_confidence" | "unverified";
  onClick: () => void;
}

// Visual:
// ✅ [1] — green dot, normal weight
// ⚠️ [2] — amber dot, tooltip on hover
// (unverified citations are never shown)
```

### SourcePanel (slide-in)
```tsx
interface SourcePanelProps {
  citation: Citation;
  isOpen: boolean;
  onClose: () => void;
}

// Content:
// - Source metadata header (Title, Edition, Year)
// - Highlighted excerpt from the chunk
// - PDF viewer at cited page (react-pdf)
// - "Open full source" link
// - For tables: rendered markdown table
// - For figures: image + caption
```

### CitationCard (below response)
```
┌─────────────────────────────────────────────────────┐
│ [1] ✅                                              │
│ Harrison's Principles of Internal Medicine, 21st Ed │
│ Chapter 396: Diabetes Mellitus · Page 2855          │
│                                                     │
│ "Metformin is the preferred initial pharmacologic   │
│  agent for most patients with type 2 diabetes..."   │
│                                                     │
│ [View Source →]                                     │
└─────────────────────────────────────────────────────┘
```

### CorpusCard (source browser)
```
┌──────────────────────────────────────┐
│ 📗 MEDICAL                           │
│                                      │
│ Harrison's Principles of             │
│ Internal Medicine                    │
│ 21st Edition · 2022                  │
│ Loscalzo, Fauci, et al.              │
│                                      │
│ 40,234 chunks indexed                │
│                                      │
│ [Browse Source →]                    │
└──────────────────────────────────────┘
```

---

## User Flows

### Flow 1 — First Query (New User)
```
Landing page → Sign Up → Email verification → 
Onboarding (domain selection, what CuraSource is) → 
Chat interface → Type first query → 
Response with citations → Click citation → Source viewer
```

### Flow 2 — Returning User
```
Login → Chat interface (last session or new) → 
Query → Response → Feedback (optional)
```

### Flow 3 — Citation Exploration
```
Read response → Notice [2] with ⚠️ warning →
Hover tooltip: "matched with lower confidence" →
Click [2] → Source panel opens →
See exact page from Davidson's 24th Ed →
"View full source" → Full PDF page
```

### Flow 4 — Corpus Browser
```
Sidebar → "Corpus Browser" →
Filter by domain: Medical →
Find "Goldberger's Clinical Electrocardiography" →
Click → Source detail page →
Table of contents (chapter list) →
"Ask about this source" → Chat pre-filtered to this source
```

---

## Responsive Design

| Breakpoint | Layout |
|-----------|--------|
| Mobile < 768px | Full-screen chat, sidebar as drawer, source panel as bottom sheet |
| Tablet 768–1024px | Sidebar collapsible, source panel as modal |
| Desktop > 1024px | Three-column layout available (sidebar + chat + source panel) |

---

## Accessibility

- All interactive elements keyboard-navigable (Tab order logical)
- Citation badges have aria-label: "Citation 1, verified"
- Source panel traps focus when open (focus-trap)
- Streaming text has aria-live="polite" 
- Color is never the only indicator (status icons + text labels alongside color)
- Min contrast ratio 4.5:1 for all text
- PDF viewer has "Skip to content" for screen readers

---

## Empty & Error States

| State | Display |
|-------|---------|
| No sessions yet | Illustrated empty state: "Ask your first question" with example prompts |
| Query out of scope | Inline message: "This topic isn't in our sources. Closest match: [X]" |
| No chunks found | "No relevant information found. Try rephrasing or use a different domain filter." |
| API error | "Something went wrong. Your query was not charged. Please try again." |
| Rate limit hit | "You've used your 10 free queries today. Upgrade for more." |
| Streaming interrupted | Show partial response + "Response was interrupted. [Retry →]" |
