# Product Requirements Document (PRD)

**System Name:** ClearLedger — Financial Invoice & Payment Reconciliation Register  
**Author:** Executive Principal Product Architect  
**Version:** 1.0.0-PROD  
**Status:** Approved for Engineering Implementation  

---

## 1. EXECUTIVE SUMMARY

### Problem Statement
* **Current Manual/Flawed Workflow:** Small business finance operators track accounts receivable using fragmented spreadsheets and un-sanitized CSV imports. Existing software suffers from critical data integrity defects: retrying a CSV import causes duplicate monetary entries, open invoice balances drift out of sync with overview statistics, screen views mismatch downloaded CSV reports, and batch imports fail silently without line-level diagnostic feedback. Finance teams waste hours auditing phantom balances and untangling mismatched payments.
* **Proposed Automated Workflow:** ClearLedger introduces an immutable, deterministic financial ledger with strict identity-based reconciliation. CSV imports validate line-by-line with atomic row processing and idempotency guards (`(customer_id, invoice_number)` for invoices, `payment_id` for payments). Re-imports of identical records execute idempotently without balance movement; modified identity re-uses are cleanly rejected. The user interface updates dynamically with zero monetary rounding drift across real-time screens and downloadable reports.

### Ideal Customer Profile (ICP) & Core User Personas
* **Ideal Customer Profile (ICP):** Small-to-Medium Service Businesses (B2B/B2C service providers, agencies, regional distributors) handling 100 to 10,000 monthly invoices across established accounts with synthetic/multi-currency accounts receivable requiring zero balance variance.
* **Core User Persona — The Business Owner / Finance Operator ("Priya"):**
  * *Role:* Managing Director & Head of Finance.
  * *Context:* Manages weekly cash collection, verifies open customer invoices (`HARBOR`, `MAPLE`, `NORTH`), and imports daily bank payment dumps.
  * *Needs:* Absolute confidence that unpaid invoice totals match exported reports, single-click CSV import with exact error line numbers, and strict prevention of accidental double-counting on re-import retries.

### Primary Success Metrics
* **Activation Velocity:** Time to import first batch CSV and complete reconciliation $\le 45\text{ seconds}$ from clean initialization.
* **Conversion & Reconciliation Threshold:** $100\%$ accuracy (0 monetary drift at 2 decimal places) across stored SQLite balance calculations, UI screens, and CSV exports.
* **System Latency Limits:** 
  * API endpoints (`GET /api/overview`, `GET /api/invoices`): P99 latency $< 150\text{ms}$.
  * Batch CSV import (`POST /api/import`): Processing velocity $> 1,000\text{ records/sec}$ with total request payload up to 2 MB responding in $< 800\text{ms}$.

---

## 2. FEATURE BOUNDARIES (MoSCoW Framework)

```
+-------------------------------------------------------------------------------+
|                                  MUST HAVE                                    |
| - Strict identity & idempotency checks for invoices & payments                |
| - Atomic CSV parsing (UTF-8, <=2MB) with line-by-line validation & error logs |
| - Precise 2-decimal place currency accounting with overpayment support        |
| - HTTP endpoints: GET /api/overview, GET /api/invoices, GET /api/export       |
| - Dynamic UI refresh agreeing strictly with database register state          |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
|                                 SHOULD HAVE                                   |
| - TypeSafe System One (Jev) semantic CSV header & anomaly classification      |
| - Detailed filter controls (customer_id, date range) on open invoices        |
| - Export filtering matching active screen view parameters                     |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
|                                 COULD HAVE                                    |
| - TypeSafe probability-scored automated candidate matching for unmatched      |
| - Interactive manual payment-to-invoice re-attachment UI                      |
+-------------------------------------------------------------------------------+
                                        |
+-------------------------------------------------------------------------------+
|                                 WON'T HAVE (V1)                               |
| - Tax / GST calculation engines or foreign exchange (FX) conversion           |
| - Automatic retroactive re-matching of historical unmatched payments          |
| - Multi-tenant user authentication, RBAC, or concurrent write locking         |
+-------------------------------------------------------------------------------+
```

### Must Have (Core MVP Loop — Non-Negotiable)
1. **Strict Idempotency & Identity Enforcement:**
   * Invoices identified by `(customer_id, invoice_number)`. Re-importing identical details skips without altering balances. Re-using identity with altered amount/due date rejects row and preserves existing data.
   * Payments identified by `payment_id`. Re-importing identical payment skips; re-using `payment_id` with conflicting attributes rejects row.
   * Payments attach **only** when both `customer_id` and `invoice_number` match an existing invoice. Unmatched payments retained in `unmatched_payments` pool without reducing invoice balances.
2. **Deterministic CSV Import Processing Engine:**
   * UTF-8 decoding (with optional BOM support). Max file size 2 MB.
   * Strict header validation (Exact order for Invoices: `customer_id,invoice_number,amount,due_date`; Payments: `payment_id,customer_id,invoice_number,amount`). Header failure rejects entire payload (HTTP 400).
   * Row-level atomic processing: invalid data rows are rejected individually with line numbers and descriptive reasons while valid rows commit successfully (HTTP 200).
3. **Financial Accounting Engine:**
   * Money calculations strictly preserved at 2 decimal places (cents/paise precision).
   * Overpayments permitted (negative balance, status set to `paid`). Overpayments on invoice $A$ do not reduce balance on invoice $B$.
   * Overview summary metrics: `outstanding` = exact sum of positive invoice balances; `open_count` = total invoices with balance $> 0.00$.
4. **Preserved HTTP API Interface:**
   * `GET /api/overview`: Returns `{ summary, invoices, unmatched_payments }`.
   * `GET /api/invoices?status={all|open|paid}`: Returns status-filtered invoice array; invalid status returns HTTP 400.
   * `GET /api/export`: Returns CSV export matching active invoice table (`customer_id,invoice_number,amount,paid,balance,status`).
   * `POST /api/import?kind={invoices|payments}`: Raw CSV import returning `{ imported, skipped, rejected, errors }`.
5. **UI Consistency & Real-Time Synchronization:**
   * UI table automatically re-fetches register state post-import to eliminate client-server divergence.

### Should Have (Post-Launch Enhancements)
1. **TypeSafe System One Semantic Anomaly Detection:** Integrate TypeSafe `noul` and `choice` primitives to flag suspicious customer invoice spikes or anomalous payment amounts prior to database transaction commit.
2. **Advanced Multi-Column Filtering:** Filter invoice views by `customer_id` and due date ranges with instant UI re-render.
3. **Structured Audit Trail Export:** Export rejected CSV row logs as downloadable diagnostic JSON/CSV reports.

### Could Have (Exploratory / V1.1)
1. **Intelligent Unmatched Payment Suggestions:** Use TypeSafe `score` primitive to rank unmatched payment candidates against unattached open invoices by proximity of amount and date.
2. **Visual Reconciliation Canvas:** Interactive drag-and-drop allocation of unmatched payments to open invoices.

### Won't Have (Explicitly Forbidden for V1)
1. Multi-currency exchange rate conversions (FX) or tax calculations.
2. Automatic retroactive rematching of historical unmatched payments upon new invoice arrival.
3. Multi-user concurrent session locking or RBAC authentication layers.

---

## 3. USER STORIES & GHERKIN ACCEPTANCE CRITERIA

### Workflow 1: Idempotent Re-Import of Existing Invoices
**Story:** As a Finance Operator, I want to re-import a previously processed invoice CSV file so that I can retry imports without creating duplicate records or altering existing totals.

```gherkin
Feature: Idempotent Invoice CSV Import Processing

  Scenario: Re-importing identical invoice CSV yields zero count changes and zero balance drift
    Given the system register contains an existing invoice for customer "HARBOR" with number "INV-1001", amount 500.00, and due date "2026-10-01"
    And the overview total outstanding is 500.00
    When the user POSTs a raw CSV file to "/api/import?kind=invoices" with header "customer_id,invoice_number,amount,due_date" and content:
      """
      HARBOR,INV-1001,500.00,2026-10-01
      """
    Then the HTTP response code must be 200
    And the response JSON payload must be:
      | field    | value |
      | imported | 0     |
      | skipped  | 1     |
      | rejected | 0     |
    And the database invoice record for "HARBOR", "INV-1001" must remain amount 500.00 with paid 0.00 and balance 500.00
    And the overview total outstanding must remain exactly 500.00
```

### Workflow 2: Rejection of Conflicting Invoice Identity Re-Use
**Story:** As a Finance Operator, I want the system to reject any CSV row that re-uses an existing invoice identifier with different amounts or due dates so that historical financial records cannot be corruptly overwritten.

```gherkin
Feature: Rejection of Conflicting Identity Overwrites

  Scenario: CSV row re-using invoice key with modified amount is rejected while valid row processes
    Given the system register contains invoice "MAPLE", "INV-2002" with amount 1200.00
    When the user POSTs a raw CSV file to "/api/import?kind=invoices" containing:
      | line | customer_id | invoice_number | amount  | due_date   |
      | 2    | MAPLE       | INV-2002       | 1500.00 | 2026-11-15 |
      | 3    | NORTH       | INV-3003       | 450.00  | 2026-11-20 |
    Then the HTTP response status code must be 200
    And the response JSON payload must indicate:
      | property | value |
      | imported | 1     |
      | skipped  | 0     |
      | rejected | 1     |
    And the error list must contain line 2 with reason matching "conflicting details"
    And invoice "MAPLE", "INV-2002" must retain its original amount of 1200.00
    And new invoice "NORTH", "INV-3003" must be created with amount 450.00
```

### Workflow 3: Payment Allocation & Unmatched Payment Retention
**Story:** As a Finance Operator, I want imported payments to attach exclusively to matching customer-invoice pairs and unattached payments to be stored in an unmatched pool so that invoice balances are only credited by legitimate payments.

```gherkin
Feature: Payment Attachment and Unmatched Allocation

  Scenario: Processing a payment CSV with one matching payment and one unmatched payment
    Given an open invoice exists for customer "NORTH", "INV-5001" with amount 800.00 and paid 0.00
    When the user POSTs a payment CSV to "/api/import?kind=payments" containing:
      | payment_id | customer_id | invoice_number | amount |
      | PAY-801    | NORTH       | INV-5001       | 300.00 |
      | PAY-802    | HARBOR      | INV-9999       | 150.00 |
    Then the HTTP response code must be 200
    And invoice "NORTH", "INV-5001" must update to paid 300.00 and balance 500.00
    And invoice "NORTH", "INV-5001" status must remain "open"
    And payment "PAY-802" must be appended to the unmatched_payments database table
    And "GET /api/overview" must include "PAY-802" in the "unmatched_payments" list
    And payment "PAY-802" must NOT reduce any invoice balance in the system
```

### Workflow 4: Synchronized Overview, Invoices View, and CSV Export
**Story:** As a Finance Operator, I want the UI overview summary, invoice table, and downloadable CSV report to display identical financial totals so that my internal reporting has zero balance discrepancies.

```gherkin
Feature: Multi-Surface Financial Data Synchronization

  Scenario: Requesting invoice listing, overview summary, and CSV export after overpayment
    Given invoice "HARBOR", "INV-7001" has amount 200.00 and attached payment 250.00 (balance -50.00, status "paid")
    And invoice "MAPLE", "INV-7002" has amount 400.00 and attached payment 0.00 (balance 400.00, status "open")
    When a request is executed for "GET /api/overview"
    Then the summary payload "outstanding" must equal 400.00
    And the summary payload "open_count" must equal 1
    When a request is executed for "GET /api/invoices?status=open"
    Then the returned array must contain exactly 1 invoice ("INV-7002")
    When a request is executed for "GET /api/export"
    Then the response Content-Type must be "text/csv"
    And the exported CSV line for "INV-7001" must state "HARBOR,INV-7001,200.00,250.00,-50.00,paid"
    And the exported CSV line for "INV-7002" must state "MAPLE,INV-7002,400.00,0.00,400.00,open"
```

### Workflow 5: Atomic Error Recovery on Partial CSV Import
**Story:** As a Finance Operator, I want an import file with malformed data rows to reject only those specific bad rows while applying valid rows so that valid business entries are never blocked by isolated row typos.

```gherkin
Feature: Row-Level Atomic Import Validation

  Scenario: Importing CSV with header intact but mixed row validity
    Given a clean database register
    When the user POSTs an invoice CSV to "/api/import?kind=invoices" with lines:
      """
      customer_id,invoice_number,amount,due_date
      HARBOR,INV-101,150.50,2026-12-01
      MAPLE,INV-102,-50.00,2026-12-01
      UNKNOWN_CUST,INV-103,200.00,2026-12-01
      NORTH,INV-104,300.00,2026-12-32
      NORTH,INV-105,500.00,2026-12-05
      """
    Then the HTTP status code must be 200
    And the JSON response fields must be:
      | field    | value |
      | imported | 2     |
      | skipped  | 0     |
      | rejected | 3     |
    And the "errors" array must contain 3 items:
      | line | reason_contains                                  |
      | 3    | positive decimal                                 |
      | 4    | customer must exist                              |
      | 5    | valid YYYY-MM-DD date                            |
    And invoices "INV-101" and "INV-105" must exist in the database
```

---

## 4. NON-FUNCTIONAL REQUIREMENTS

### Performance & Core Web Vitals
* **Largest Contentful Paint (LCP):** $\le 1.2\text{ seconds}$ on standard desktop networks ($100\text{ Mbps}$).
* **Interaction to Next Paint (INP):** $\le 200\text{ milliseconds}$ across all interactive buttons (Import, Filter, Export).
* **Cumulative Layout Shift (CLS):** $\le 0.10$ during initial page render and dynamic table re-hydration.
* **Database IO Performance:** SQLite transactions must execute within single atomic write transactions with `WAL` (Write-Ahead Logging) mode enabled to guarantee sub-millisecond query execution.

### Security Standards & Compliance
* **OWASP Top 10 Mitigations:**
  * *SQL Injection:* $100\%$ parameterized SQL queries across all database drivers. No dynamic string interpolation in SQL constructs.
  * *XSS (Cross-Site Scripting):* HTML context escaping on all user-supplied CSV string properties rendered in the DOM (`customer_id`, `invoice_number`, `payment_id`).
  * *Input Sanitization:* Rejection of control characters, dangerous script tags, and non-UTF8 sequences. Strict string trimming on all CSV tokens.
  * *Request Body Boundaries:* Hard limits on payload size ($2\text{ MB}$) to prevent Denial of Service (DoS) memory exhaustion.

### Accessibility (a11y)
* **WCAG 2.1 Level AA Compliance:**
  * Full keyboard traversability (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`) across table filters, file upload inputs, and modal dialogs.
  * Semantic HTML5 tagging (`<main>`, `<nav>`, `<header>`, `<table>`, `<thead>`, `<tbody>`, `<caption>`).
  * Explicit `aria-labels` and `aria-live="polite"` regions for dynamic import status notifications and error toasts.
  * Minimum color contrast ratio of $4.5:1$ for normal text and $3:1$ for heavy UI controls against the background color palette.

---

## 5. ARCHITECTURE & TYPESAFE SYSTEM ONE INTEGRATION GUIDE

### TypeSafe Primitive Mapping Strategy
To deliver intelligent common sense and automated decision primitives without fragile, unstructured LLM prompt parsing, ClearLedger incorporates TypeSafe System One (`Jev`) primitives for incoming transaction validation:

```
+-----------------------------------------------------------------------------------+
|                            INCOMING CSV / PAYMENT EVENT                           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        TYPESAFE SYSTEM ONE (JEV) INFERENCE                        |
|                                                                                   |
|  1. Noul Primitive ("anomalous_amount"):                                          |
|     State: { customer_id, historical_avg, incoming_amount }                       |
|     Criteria: Evaluates probability of extreme magnitude anomaly.                 |
|                                                                                   |
|  2. Choice Primitive ("header_mapping"):                                          |
|     State: { uploaded_raw_header }                                                |
|     Criteria: Maps non-standard uploaded columns to expected canonical schema.    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                          DETERMINISTIC SQLITE LEDGER ENGINE                       |
|   Executes strict idempotent balance update and persistence transaction.          |
+-----------------------------------------------------------------------------------+
```

1. **Noul Primitive (`anomalous_amount`):** Evaluates incoming payment amount against customer historical baseline to compute anomaly probability $P(\text{anomaly})$. If $P(\text{anomaly}) > 0.85$, the system flags the transaction for manual review while preserving raw input.
2. **Choice Primitive (`header_mapping`):** Maps non-standard incoming third-party CSV headers to canonical `(customer_id, invoice_number, amount, due_date)` structure via deterministic single-token choice evaluation.
