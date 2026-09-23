# Repository Brain & Architectural Governance

**System Name:** ClearLedger — Financial Invoice & Payment Reconciliation Register  
**Author:** AI Agent Systems Architect  
**Version:** 1.0.0-BRAIN  
**Status:** Authoritative Repository Invariant  

---

## 1. SYSTEM CORE ESSENCE

ClearLedger is an immutable, deterministic financial invoice and payment reconciliation system designed for small business finance operators to track accounts receivable with zero balance drift. The system provides atomic, row-level CSV import processing, strict identity-based payment matching, and real-time synchronization across UI views and downloadable reports. Built on a Next.js 15 App Router architecture with PostgreSQL 16 (Drizzle ORM), Supabase Auth, and TypeSafe System One (`Jev`) AI inference primitives, it eliminates double-counting, silently dropped imports, and financial discrepancies.

---

## 2. STRICT ARCHITECTURAL COMMANDMENTS (Zero-Tolerance Invariants)

### 1. Type Safety & Validation Boundaries
* **Zero `any` Types:** The compilation flag `"noImplicitAny": true` is enforced. Never introduce `any` or untyped `as target` casting.
* **Strict Zod Boundary Validation:** All API request bodies, CSV row tokens, route parameters, and environment variables MUST be parsed using Zod schemas at the network boundary before entering core domain logic.
* **Tabular Currency Precision:** All monetary amounts MUST be computed at 2 decimal places (cents/paise) using exact numeric representations (`NUMERIC(12, 2)` or integer cents) to prevent IEEE 754 floating-point rounding drift.

### 2. React Server Components & Client Boundaries
* **Server Components First:** All page routes and data containers default to React Server Components (RSC).
* **Restricted `"use client"` Directives:** `"use client"` is restricted solely to isolated leaf components requiring DOM event listeners (`onClick`, `onDrop`), React state (`useState`, `useReducer`), or browser hooks (`useQuery`).

### 3. Styling & Token Architecture
* **Semantic Token Enforcement:** All styles MUST use Tailwind CSS v4 custom variables defined in `DESIGN_SYSTEM.md` (e.g., `var(--brand-primary)`, `var(--surface-card)`).
* **No Hardcoded Hex Values or Arbitrary Pixel Margins:** Hardcoded colors (`#1D4ED8`, `#0F172A`) or arbitrary pixel values (`p-[13px]`) are strictly forbidden. Use 4px baseline grid spacing utilities (`space-1` through `space-16`).

### 4. Database Mutations & Financial Transactions
* **Atomic ORM Mutations:** All multi-row database updates (e.g., payment insertion + invoice balance recalculation + import log entry) MUST be executed inside single atomic `db.transaction()` blocks via Drizzle ORM.
* **Parameterized SQL & RLS:** No raw string interpolation in SQL queries. Row Level Security (RLS) policies MUST be enforced on all PostgreSQL tables.

---

## 3. DIRECTORY TOPOLOGY MAP

```text
e:\Mystri-Applicant-Assessments\track-a/
├── .agents/
│   └── skills/
│       └── typesafe-ai/
│           └── SKILL.md                 # TypeSafe System One Skill Integration
├── app.py                               # Flask/Python legacy server runner
├── restore_fixture.py                   # Preserved fixture database loader script
├── BUSINESS_RULES.md                    # Canonical business logic specification
├── README.md                            # Starter documentation & track instructions
├── PRD.md                               # Product Requirements Document
├── TRD.md                               # Technical Requirements Document
├── DESIGN_SYSTEM.md                     # UI/UX Token Architecture & CSS Specification
├── APP_FLOW.md                          # App Flow, Sitemap & State Machine Spec
├── brain.md                             # Authoritative Repository Governance (This file)
│
├── ledger/                              # Backend ledger domain engine
│   ├── database.py                      # SQLite database connection & schema initialization
│   ├── models.py                        # Invoice & Payment data structures
│   ├── import_engine.py                 # Atomic CSV parser & validator
│   └── matching.py                      # Identity matching & balance calculations
│
├── web/                                 # Frontend Web UI Layer
│   ├── index.html                       # Base HTML structure
│   ├── styles.css                       # Design System CSS variables & layout styles
│   └── app.js                           # Frontend controller & fetch handler
│
├── fixtures/                            # Existing owner register fixtures to preserve
│   ├── existing-register.sqlite3        # Preserved SQLite database fixture
│   └── expected-records.json            # Target verification test assertions
│
└── tests/                               # Test suite
    ├── test_smoke.py                    # Smoke test suite
    └── test_reconciliation.py           # Integrity & regression test checks
```

---

## 4. PROGRESS TRACKER & REPOSITORY LEDGER

### Completed Milestones
- [x] Installed and registered `typesafe-ai` agent skill in `.agents/skills/typesafe-ai/SKILL.md`.
- [x] Authored production-grade **Product Requirements Document (PRD.md)** covering MoSCoW features, Gherkin criteria, and success metrics.
- [x] Authored production-grade **Technical Requirements Document (TRD.md)** specifying Next.js 15 RSC architecture, PostgreSQL DDL script, RLS policies, and Zod contracts.
- [x] Authored production-grade **UI/UX Design System Specification (DESIGN_SYSTEM.md)** defining HSL/HEX tokens, typography scale, 4px grid, and Tailwind CSS configuration.
- [x] Authored production-grade **App Flow & State Machine Specification (APP_FLOW.md)** detailing sitemap, Mermaid.js flowcharts, screen interaction matrix, and optimistic UI protocols.
- [x] Authored authoritative repository governance context **(brain.md)**.

### In-Progress Task (Current Focus)
- [ ] Executing defect investigation and repair of ClearLedger seeded defects across import, matching, and reporting engines while preserving existing fixtures.

### Up Next (Queued Backlog)
- [ ] Implement atomic line-by-line CSV import error tracking with explicit line numbers and failure reasons.
- [ ] Enforce strict identity checking `(customer_id, invoice_number)` for invoices and `payment_id` for payments.
- [ ] Align screen overview numbers, invoice list totals, and CSV export records to ensure zero monetary rounding drift.
- [ ] Implement TypeSafe System One anomaly flagging primitive for incoming payment imports.
- [ ] Create comprehensive regression test suite verifying fix validity and fixture preservation.
- [ ] Generate final `HANDOVER.md` report.

### Known Technical Debt & Blockers
- **Legacy Python Engine:** Current app runner uses `app.py` and SQLite; TRD specifies Next.js 15 + PostgreSQL target architecture for production scaling. Repairs on `track-a` must preserve the public API routes (`/api/overview`, `/api/invoices`, `/api/export`, `/api/import`).

---

## 5. RAPID CONTEXT POINTERS

* **Product Requirements:** [PRD.md](file:///e:/Mystri-Applicant-Assessments/track-a/PRD.md)
* **Technical Requirements:** [TRD.md](file:///e:/Mystri-Applicant-Assessments/track-a/TRD.md)
* **Design System & CSS Tokens:** [DESIGN_SYSTEM.md](file:///e:/Mystri-Applicant-Assessments/track-a/DESIGN_SYSTEM.md)
* **App Flow & State Machines:** [APP_FLOW.md](file:///e:/Mystri-Applicant-Assessments/track-a/APP_FLOW.md)
* **Business Rules Specification:** [BUSINESS_RULES.md](file:///e:/Mystri-Applicant-Assessments/track-a/BUSINESS_RULES.md)
* **TypeSafe Integration Skill:** [SKILL.md](file:///e:/Mystri-Applicant-Assessments/track-a/.agents/skills/typesafe-ai/SKILL.md)
* **Repository Governance:** [brain.md](file:///e:/Mystri-Applicant-Assessments/track-a/brain.md)
