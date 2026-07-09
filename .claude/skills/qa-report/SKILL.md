---
name: qa-report
description: >-
  Execute a client-review / QA punch-list on this Shopify store / theme and
  produce a single reviewable before/after report. For each item: capture the
  broken state (URL + screenshot), apply the fix, verify it live on the published
  storefront, capture the fixed state — storing evidence per item — then compile
  everything into one self-contained HTML Artifact (before/after pairs, status
  pills, an "awaiting client" section). Use when asked to "work the client
  feedback / review list", "fix these and show before/after", "document what
  changed with proof", or "make a QA report". Inputs: the feedback source (a doc,
  meeting notes, or a list of items) and the store URL (the live storefront, or a
  theme-preview URL while iterating).
---

# QA Report — fix a review list, prove every change

Turns a messy client-review list into (1) a set of verified live fixes and
(2) one artifact the client can review in a single pass. The value is the
**evidence discipline**: nothing is "done" until it's shown broken, shown fixed,
and confirmed live on the storefront.

## What it produces

- `.qa-evidence/<item>/` per item — `notes.md` + `before-*` / `after-*`
  screenshots. Add `.qa-evidence/` to `.gitignore` if it isn't already.
- One self-contained HTML report published via the **Artifact** tool: before/after
  image pairs, a stat band, per-item status, and a "waiting on client" section.

## Dependencies (works standalone)

The core of this skill — the capture → fix → verify → evidence loop, the report
template, and `scripts/build-report.py` — is **self-contained**: it needs only
Python 3 with Pillow, plus a browser driver for screenshots (e.g. chrome-devtools).
No API keys, no other skill required.

The **fix** step uses this project's own Shopify tooling: Liquid edits in the theme
(`sections/`, `snippets/`, `templates/`, `config/`), theme settings, and the
Shopify Admin (products, collections, metafields, navigation, URL redirects) via
the Shopify MCP or admin. Fix imagery/copy at its real source; don't invent
content to fill a gap — park it instead (step 5).

## Process

### 1. Consolidate the list
Merge every source (feedback doc, meeting transcript, inline asks) into one
numbered work-list. Keep the client's own item IDs (B1, C5, …) — they're how the
client refers back. Batch them into a task list before starting.

### 2. Per item: capture → fix → verify → capture
For **each** item, in order:

1. **Before.** Load the affected URL, confirm the defect, screenshot it. Record
   the exact URL, the repro, and the Liquid section/snippet or Admin resource at
   fault in `.qa-evidence/<item>/notes.md`. For a data problem, capture the proof
   in the shape it lives (a `curl -I` status, a product/metafield value, a
   redirect target) — not just a picture.
2. **Fix.** Use whatever fits the change — a Liquid/section/settings edit for
   layout and copy in the theme, or the Shopify Admin for products, collections,
   metafields, menus, and URL redirects. Respect the store's content and brand
   rules; don't guess imagery or identities.
3. **Verify LIVE on the storefront** (see Verification below). A change that only
   looks right in the theme editor or an unpublished preview is **not** done —
   verify on the published theme / live URL the customer actually sees.
4. **After.** Re-load the live URL, screenshot the fixed state, write the AFTER
   block in `notes.md` with the verification result.

Screenshots: drive `chrome-devtools` (load its tools via ToolSearch) against the
**live storefront URL** and save with `filePath`. Name them `before-N-*` /
`after-N-*` so the manifest keys are obvious later.

### 3. Sweep beyond the explicit list
The client names symptoms, not every instance. When an item reflects a **rule**
(a spacing standard, a recurring section pattern, a class of broken link or
missing alt text), inventory the whole store — every template and key
collection/product page — for other violations and fix them too, but log what you
swept and what you deliberately left.

### 4. Compile the report
1. Duplicate `assets/report-template.html` (a re-skinnable reference — masthead,
   stat band, item card, before/after grid, redirect table, awaiting-client card).
   Swap the palette / copy for this store's brand.
2. Rewrite the copy for this review. Each image slot is a `__IMG_<key>__` token.
   Write plain, client-facing copy: *Reported → Cause → Fixed*, active voice.
3. Build a manifest `{ "<key>": "<abs path to the evidence image>", … }` pointing
   at the real `.qa-evidence/**` files (the builder downscales them — no manual
   staging).
4. Run the builder:
   ```bash
   python3 .claude/skills/qa-report/scripts/build-report.py \
     --template <report.template.html> --manifest <images.json> \
     --out <report.html> [--max 900] [--quality 72]
   ```
   It inlines every token as a base64 JPEG data URI and **refuses to write** if a
   token is unmatched or a source is unreadable (so a broken report never ships).
5. Sanity-check the render (open the file in a browser / chrome-devtools, screenshot
   a couple of sections), then publish with the **Artifact** tool. Favicon `🔧`.

### 5. Park what's blocked — don't guess
If an item needs a client asset (an approved product photo, brand imagery,
copy sign-off) and proceeding would mean inventing or guessing content, **stop and
document it** in a `BLOCKED.md`: what was asked, why it's blocked, and the exact
list of what's needed to unblock. Surface these in the report's "Waiting on
client" section, each with a *To unblock* list.

## Verification (Shopify stack)

- **Verify on the PUBLISHED theme, not the editor.** The theme editor and an
  unpublished preview can differ from what customers see. Confirm the change on the
  live storefront URL (or, while iterating, the specific `?preview_theme_id=`
  URL — but the definitive check is the published theme).
- **Bust the CDN cache.** Shopify serves theme assets and images from its CDN.
  After an asset/image change, hard-refresh or append a cache-buster query param;
  confirm the new asset actually loads (check the response URL / status), not a
  stale cached copy.
- **URL redirects** live in the Admin (Online Store → Navigation → URL Redirects).
  Test end-to-end (follow the source with `curl -L -w '%{http_code}|%{url_effective}'`);
  a destination that 404s is a dead redirect.
- **Product / metafield data:** verify the rendered value on the live product or
  collection page, not just the Admin field — theme logic can hide or transform it.
- **Follow the doc, but trust your eyes.** Items the client marked "done" have been
  wrong before — verify each one yourself on the live storefront.

## Report design (re-skinnable reference — in the template)

Utilitarian-but-polished. The template ships with a neutral default palette
(dark-blue masthead, one warm accent, off-white ground, green = live, amber =
awaiting) — swap the CSS vars for this store's brand. Structure: stat band →
grouped sections → item cards (`Reported / Cause / Fixed` rows + a before/after
grid + a mono technical footnote) → an amber "Waiting on client" section.

Self-contained only: the Artifact CSP blocks all remote hosts — no font CDNs, no
remote images. Everything is inlined by the builder. Write the file as page content
(no doctype/html/head/body — the publisher wraps it).

## Checkpoints
- Every completed item has a before AND an after, and the after is verified on the
  published storefront.
- Image/asset changes were confirmed live past the CDN cache.
- The sweep is logged (what was checked, what was left, and why).
- Blocked items are parked with a concrete *To unblock* list, never guessed.
- The built report has zero leftover `__IMG_` tokens (the builder enforces this).
