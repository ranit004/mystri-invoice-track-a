# UI/UX Design System Specification & Token Architecture

**System Name:** ClearLedger Design System (ClearUI)  
**Author:** Principal Design Systems Architect & Creative Director  
**Version:** 1.0.0-DESIGN  
**Status:** Production Ready  

---

## 1. DESIGN AESTHETIC & PHILOSOPHY

### Visual Tone: Precision Data-Dense Slate & Financial Integrity Glassmorphism
ClearLedger is built for finance operators who manage high-volume customer accounts and daily cash registers. The design system prioritizes **uncompromising legibility, sub-pixel alignment, high data density, and immediate feedback**.

* **Zero-Drift Spatial Grid:** Built on an strict 4px baseline grid. Every table cell, status badge, input height, and icon aligns to integer grid increments.
* **Monochrome Slate Canvas with Functional Semantic Signals:** Neutral slate surfaces prevent visual fatigue during long reconciliation sessions. Color is reserved strictly for semantic states (e.g., Emerald for Paid/Matching, Amber for Open/Unmatched, Rose for Rejections/Conflicting data, Indigo for AI/TypeSafe System One inferences).
* **Tactile Elevation & Sub-Pixel Borders:** Depth is established through subtle 1px border contrasts (`hsla(215, 20%, 88%, 0.6)`) and layered box shadows with inner highlight offsets rather than heavy blurred drop shadows.

---

## 2. COLOR TOKEN TAXONOMY

### Complete HSL & HEX Color Palette

#### Light Mode Palette

| Token Name | HSL Value | HEX Equivalent | Usage & Role |
| --- | --- | --- | --- |
| `--bg-canvas` | `hsl(210, 20%, 98%)` | `#F8FAFC` | Main application background canvas |
| `--surface-elevated` | `hsl(0, 0%, 100%)` | `#FFFFFF` | Elevated card containers, modals, table wrappers |
| `--surface-card` | `hsl(214, 15%, 95%)` | `#F1F5F9` | Secondary panel, summary metric cards |
| `--surface-popover` | `hsl(0, 0%, 100%)` | `#FFFFFF` | Dropdown menus, tooltips, combobox popovers |
| `--text-primary` | `hsl(222, 47%, 11%)` | `#0F172A` | Primary body text, table data cells, headers (100% opacity) |
| `--text-secondary` | `hsl(215, 16%, 35%)` | `#334155` | Secondary labels, table column headers (70% opacity) |
| `--text-muted` | `hsl(215, 14%, 55%)` | `#64748B` | Helper captions, placeholder text, metadata (45% opacity) |
| `--text-disabled` | `hsl(214, 12%, 72%)` | `#94A3B8` | Disabled buttons, inactive tab labels |
| `--brand-primary` | `hsl(224, 76%, 48%)` | `#1D4ED8` | Primary interactive buttons, active tab borders |
| `--brand-secondary` | `hsl(226, 70%, 55%)` | `#2563EB` | Hover states, secondary action accents |
| `--brand-accent` | `hsl(262, 83%, 58%)` | `#7C3AED` | TypeSafe System One AI indicator badges & highlights |
| `--status-success` | `hsl(158, 64%, 38%)` | `#047857` | Paid invoice status, successfully imported CSV rows |
| `--status-warning` | `hsl(38, 92%, 44%)` | `#D97706` | Open balance alerts, unmatched payment warnings |
| `--status-destructive` | `hsl(346, 84%, 50%)` | `#E11D48` | CSV line rejections, conflicting identity errors |
| `--status-info` | `hsl(199, 89%, 43%)` | `#0284C7` | Informational toasts, status updates |
| `--border-subtle` | `hsl(214, 15%, 91%)` | `#E2E8F0` | Table row dividers, subtle card separators |
| `--border-default` | `hsl(214, 13%, 82%)` | `#CBD5E1` | Input outlines, card borders, tab bar baseline |
| `--border-active` | `hsl(224, 76%, 48%)` | `#1D4ED8` | Focus ring outline, active select state |

#### Dark Mode Palette

| Token Name | HSL Value | HEX Equivalent | Usage & Role |
| --- | --- | --- | --- |
| `--bg-canvas` | `hsl(224, 71%, 4%)` | `#020617` | Main dark background canvas |
| `--surface-elevated` | `hsl(222, 47%, 9%)` | `#0F172A` | Elevated dark card containers & table wrappers |
| `--surface-card` | `hsl(217, 33%, 13%)` | `#1E293B` | Dark metric cards & sidebar background |
| `--surface-popover` | `hsl(222, 47%, 10%)` | `#0F172A` | Dark dropdown menus & tooltips |
| `--text-primary` | `hsl(210, 40%, 98%)` | `#F8FAFC` | Dark primary text (100% opacity) |
| `--text-secondary` | `hsl(215, 20%, 75%)` | `#94A3B8` | Dark secondary labels (70% opacity) |
| `--text-muted` | `hsl(215, 16%, 50%)` | `#64748B` | Dark helper text & meta (45% opacity) |
| `--text-disabled` | `hsl(215, 14%, 32%)` | `#334155` | Dark disabled state text |
| `--brand-primary` | `hsl(217, 91%, 60%)` | `#3B82F6` | Dark mode primary brand color |
| `--brand-secondary` | `hsl(213, 94%, 68%)` | `#60A5FA` | Dark mode interactive hover state |
| `--brand-accent` | `hsl(263, 70%, 68%)` | `#A78BFA` | Dark mode TypeSafe System One AI indicator |
| `--status-success` | `hsl(158, 64%, 52%)` | `#10B981` | Dark mode success state |
| `--status-warning` | `hsl(38, 92%, 56%)` | `#F59E0B` | Dark mode warning state |
| `--status-destructive` | `hsl(346, 87%, 65%)` | `#F43F5E` | Dark mode destructive state |
| `--status-info` | `hsl(199, 89%, 60%)` | `#38BDF8` | Dark mode info state |
| `--border-subtle` | `hsl(217, 33%, 16%)` | `#1E293B` | Dark subtle table row dividers |
| `--border-default` | `hsl(215, 25%, 27%)` | `#334155` | Dark input outlines & card borders |
| `--border-active` | `hsl(217, 91%, 60%)` | `#3B82F6` | Dark focus ring outline |

---

## 3. TYPOGRAPHY MATRIX

### Font Family Selections
* **Primary UI Font:** `Plus Jakarta Sans` or `Inter` (Google Fonts) — Optimized for crisp rendering of tabular UI controls, forms, and headings.
* **Monospace Data Font:** `JetBrains Mono` or `Roboto Mono` (Google Fonts) — Enforces tabular numbers (`font-variant-numeric: tabular-nums`) so that monetary values, IDs, and CSV line numbers align vertically.

### Modular Type Scale Matrix

| Scale Element | Font Size (rem / px) | Line Height | Letter Spacing (Tracking) | Font Weight | CSS Utility Class |
| --- | --- | --- | --- | --- | --- |
| **Display Header** | `2.25rem` / `36px` | `1.2` (`2.7rem`) | `-0.025em` (`-0.9px`) | 700 (Bold) | `.text-display` |
| **Heading 1 (H1)** | `1.75rem` / `28px` | `1.25` (`2.2rem`) | `-0.02em` (`-0.56px`) | 700 (Bold) | `.text-h1` |
| **Heading 2 (H2)** | `1.25rem` / `20px` | `1.35` (`1.7rem`) | `-0.015em` (`-0.3px`) | 600 (SemiBold) | `.text-h2` |
| **Heading 3 (H3)** | `1.00rem` / `16px` | `1.4` (`1.4rem`) | `-0.01em` (`-0.16px`) | 600 (SemiBold) | `.text-h3` |
| **Body Default** | `0.875rem` / `14px` | `1.5` (`1.31rem`) | `0.0em` (`0.0px`) | 400 (Regular) | `.text-body` |
| **Body Medium** | `0.875rem` / `14px` | `1.5` (`1.31rem`) | `0.0em` (`0.0px`) | 500 (Medium) | `.text-body-medium` |
| **Table Data (Mono)**| `0.875rem` / `14px` | `1.4` (`1.22rem`) | `0.01em` (`0.14px`) | 500 (Medium) | `.text-mono-data` |
| **Caption / Badge** | `0.75rem` / `12px` | `1.4` (`1.05rem`) | `0.02em` (`0.24px`) | 600 (SemiBold) | `.text-caption` |
| **Micro Code / Line** | `0.6875rem` / `11px`| `1.3` (`0.89rem`) | `0.03em` (`0.33px`) | 500 (Medium) | `.text-micro` |

---

## 4. SPACING, ELEVATION & BORDER RADIUS TOKENS

### 4px Baseline Spacing Tokens

| Token | Size (rem) | Pixel Value | Typical Application |
| --- | --- | --- | --- |
| `--space-1` | `0.25rem` | `4px` | Micro-gap between badge icon and text, compact padding |
| `--space-2` | `0.50rem` | `8px` | Button inline icon spacing, input vertical padding |
| `--space-3` | `0.75rem` | `12px` | Form field internal padding, table cell vertical padding |
| `--space-4` | `1.00rem` | `16px` | Default card padding, table cell horizontal padding |
| `--space-6` | `1.50rem` | `24px` | Section grid gaps, modal internal padding |
| `--space-8` | `2.00rem` | `32px` | Main dashboard grid gap, header bottom margin |
| `--space-12` | `3.00rem` | `48px` | Outer page canvas margin |
| `--space-16` | `4.00rem` | `64px` | Empty state container vertical padding |

### Border Radius Tokens
* `--radius-sm`: `0.25rem` (`4px`) — Applied to badges, table tags, micro controls.
* `--radius-md`: `0.375rem` (`6px`) — Applied to buttons, input fields, select dropdowns.
* `--radius-lg`: `0.50rem` (`8px`) — Applied to metric cards, modals, table wrappers.
* `--radius-full`: `9999px` — Applied to round status indicators, avatar pills.

### Layered Elevation Shadows
* **Shadow Flat (`--shadow-sm`):** `0 1px 2px 0 rgba(15, 23, 42, 0.05)`
* **Shadow Card (`--shadow-md`):** `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`
* **Shadow Modal / Popover (`--shadow-lg`):** `0 10px 15px -3px rgba(15, 23, 42, 0.12), 0 4px 6px -4px rgba(15, 23, 42, 0.06)`

---

## 5. COMPONENT INTERACTION STATES

### 1. Button Interaction State Specifications

```
+---------------------------------------------------------------------------------------+
|  State     | Primary Button             | Secondary Button       | Danger Button      |
+------------+----------------------------+------------------------+--------------------+
| Default    | bg: --brand-primary        | bg: --surface-card     | bg: --status-destr |
|            | text: #FFFFFF              | border: --border-def   | text: #FFFFFF      |
+------------+----------------------------+------------------------+--------------------+
| Hover      | bg: --brand-secondary      | bg: --border-subtle    | bg: hsl(346,84%,42%)|
|            | transform: translateY(-1px)| border: --border-act   | scale: 1.01        |
+------------+----------------------------+------------------------+--------------------+
| Active     | bg: hsl(224, 76%, 40%)     | bg: --border-default   | bg: hsl(346,84%,35%)|
|            | transform: translateY(0px) | transform: scale(0.99) |                    |
+------------+----------------------------+------------------------+--------------------+
| Focus      | ring: 2px --brand-primary  | ring: 2px --brand-prim | ring: 2px --danger |
|            | offset: 2px --bg-canvas    | offset: 2px --bg-canv  | offset: 2px        |
+------------+----------------------------+------------------------+--------------------+
| Disabled   | bg: --text-disabled       | bg: --surface-card     | bg: --text-disabled|
|            | cursor: not-allowed        | opacity: 0.50          | opacity: 0.50      |
+------------+----------------------------+------------------------+--------------------+
| Loading    | opacity: 0.80              | spinner inline         | opacity: 0.80      |
|            | pointer-events: none       |                        |                    |
+---------------------------------------------------------------------------------------+
```

### 2. Form Control & Input States
* **Default State:** Border `--border-default`, background `--surface-elevated`, text `--text-primary`, transition `border-color 150ms ease, box-shadow 150ms ease`.
* **Focus-Visible State:** Border `--border-active`, box-shadow `0 0 0 3px rgba(29, 78, 216, 0.20)` (`ring-3 ring-brand-primary/20`).
* **Error State:** Border `--status-destructive`, box-shadow `0 0 0 3px rgba(225, 29, 72, 0.20)`, helper text `--status-destructive` with inline alert icon.

---

## 6. CSS VARIABLES & TAILWIND CONFIG

```css
/* ==========================================================================
   ClearLedger Production CSS Design Tokens (Tailwind v4 Compatible)
   ========================================================================== */

@layer base {
  :root {
    /* Color Tokens - Light Mode */
    --bg-canvas: #F8FAFC;
    --surface-elevated: #FFFFFF;
    --surface-card: #F1F5F9;
    --surface-popover: #FFFFFF;

    --text-primary: #0F172A;
    --text-secondary: #334155;
    --text-muted: #64748B;
    --text-disabled: #94A3B8;

    --brand-primary: #1D4ED8;
    --brand-secondary: #2563EB;
    --brand-accent: #7C3AED;

    --status-success: #047857;
    --status-warning: #D97706;
    --status-destructive: #E11D48;
    --status-info: #0284C7;

    --border-subtle: #E2E8F0;
    --border-default: #CBD5E1;
    --border-active: #1D4ED8;

    /* Spacing Tokens */
    --space-1: 0.25rem;
    --space-2: 0.50rem;
    --space-3: 0.75rem;
    --space-4: 1.00rem;
    --space-6: 1.50rem;
    --space-8: 2.00rem;

    /* Radius Tokens */
    --radius-sm: 0.25rem;
    --radius-md: 0.375rem;
    --radius-lg: 0.50rem;
    --radius-full: 9999px;

    /* Shadow Tokens */
    --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04);
    --shadow-lg: 0 10px 15px -3px rgba(15, 23, 42, 0.12), 0 4px 6px -4px rgba(15, 23, 42, 0.06);
  }

  .dark {
    /* Color Tokens - Dark Mode */
    --bg-canvas: #020617;
    --surface-elevated: #0F172A;
    --surface-card: #1E293B;
    --surface-popover: #0F172A;

    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --text-disabled: #334155;

    --brand-primary: #3B82F6;
    --brand-secondary: #60A5FA;
    --brand-accent: #A78BFA;

    --status-success: #10B981;
    --status-warning: #F59E0B;
    --status-destructive: #F43F5E;
    --status-info: #38BDF8;

    --border-subtle: #1E293B;
    --border-default: #334155;
    --border-active: #3B82F6;
  }
}

/* Tabular Mono Utility for Financial Data */
.font-mono-tabular {
  font-family: 'JetBrains Mono', 'Roboto Mono', monospace;
  font-variant-numeric: tabular-nums lining-nums;
}
```
