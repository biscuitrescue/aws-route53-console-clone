# Reference audit

Every capture of the real Route 53 console in `reference/` (private, not in the repository),
what was done with it, and what it led to. Audited on 2026-10-09 against the clone at
1920x1080, device pixel ratio 1, the viewport recorded in `reference/NOTES.md`.

Status values: `NOT INSPECTED`, `INSPECTED` (opened and read), `IN PROGRESS`, `VERIFIED`
(compared with a capture of the clone in the same state), `BLOCKED`.

| Kind | Files | Verified | Inspected only | Blocked |
|---|---|---|---|---|
| Screenshots `S##` | 108 | 61 | 47 | 0 |
| Videos `V##` | 12 | 9 | 3 | 0 |
| DOM snapshots `D##` | 19 (+4 raw HTML) | 19 | 4 | 0 |
| Notes and tools | 4 | - | 4 | 0 |

Not in `reference/` at all, so nothing to audit: S02 (password step), S43 (Test record),
V13 (sign in and out), V14 (visual-mode switch). `NOTES.md` explains why they were not captured.

## How the comparison was made

1. `reference/tools/clone/parity.mjs` drives the clone with Playwright into the state of
   each reference screenshot (same test data: `r53clone-demo.com` with one record of every
   type, `example-shop.net`, `api.r53clone-demo.com`) and writes `docs/parity/clone/`.
2. `reference/tools/clone/compare.py` pairs each capture with its reference, writes
   `docs/parity/side-by-side/` (reference left, clone right) and `docs/parity/scores.json`.
3. Each pair was looked at, at full size or as an enlarged crop of the region in question.
4. `reference/tools/clone/snapshot-diff.mjs` runs the capture kit's DevTools snapshot inside
   the clone and diffs design tokens, sticky and fixed elements and motion declarations.
5. The visible text of every DOM snapshot was checked line by line against the text the
   clone renders.

"Difference" below is the mean absolute difference per colour channel (0 identical, 255
opposite) over the compared area. It is evidence of closeness, not a claim of pixel
identity: no pair is pixel-identical, because the zone IDs, name servers, record counts and
account name differ, and because the typeface differs (see below). Values under about 6 are
pages that differ only in data and glyph shapes; higher values are pages with more data
(tables), a different scroll position, or a documented deliberate difference.

The generated images stay out of the repository (`.gitignore`: `docs/parity/*`).

## What the audit changed

Found by comparing, then fixed:

- **Typeface.** The clone rendered in Open Sans, about 6% wider than the console's Amazon
  Ember, so every line of text and every button had the wrong width. Amazon Ember is not
  licensed for reuse; 107 open fonts were measured against eight text widths recorded in
  D01. Ubuntu Sans is the closest (regular text within 1%, bold within 2%) and replaced
  Open Sans. Amazon Ember stays first in the font stack for machines that have it.
- **Header.** The logo was a placeholder wordmark; the assistant, services, CloudShell,
  bell and help buttons did nothing; the account button showed the wrong line order and
  caret; the search field only worked on Enter. All rebuilt from `dom/raw/hosted-zones-header.html`
  and S03, S08, S09, S39: real mark, services panel, help menu, notifications panel, account
  menu, live search results, "Skip to Main Content".
- **Footer.** Showed "Keyboard shortcuts", "API reference" and "Built with Cloudscape".
  Now CloudShell, Agent Toolkit for AWS, Feedback, Language, copyright, Privacy, Terms,
  Cookie preferences, at the console's positions; it wraps to two rows when narrow (S52).
- **Hosted zones list.** Side panel facts regrouped and name servers bulleted (S11);
  "0 hosted zone selected" (S22); header counter shows all zones while filtering (S13);
  filter goes straight from property to value (S12); Accelerated recovery property and
  hidden column (D02, D03); preferences use the console's toggles, 100 items by default and
  no preselected search mode (S15); clicking the name column sorts alphabetically (V09).
- **Zone page.** Details in the console's three columns (S25); Type, Routing policy and
  Alias selects moved next to the filter, with the repeated match count (S24, S28); every
  column sortable; "Delete records" when several are selected (S27); tags tab with search,
  pagination and sorting, and no split panel outside the Records tab (S30); DNSSEC tab with
  its alert and key-signing-keys table (S31); Accelerated recovery tab (S31).
- **Create hosted zone.** VPC section: info alert, Info links, "Choose VPC" search field,
  Remove VPC on the only row (S18). In-progress flash "Creating hosted zone …" (V05).
- **Edit hosted zone.** Facts stacked, not in four columns; "Value - optional" header no
  longer doubled (S21). VPC associations of a private zone can now be edited.
- **Delete dialogs.** Divider between the warning and the confirmation field (S22); column
  widths of the record list (S41).
- **Create record.** Per-record Delete button and dividers were missing (S36); "Record n"
  and "View existing records" heading sizes (S32); value field four rows high (S32); all 16
  record types and 8 routing policies listed (S33, S34); alias "Choose endpoint" and "Choose
  Region" selects (S35); the creation-method explainer shows on the first visit only (S32
  against S33); new record forms take focus (S36); in-progress flash (S38); the wizard (S37).
- **Import zone file.** "Zone file" container header; filter, sorting and pagination on the
  preview (S42).
- **Errors.** Detail line of the red flash at the console's size (S19, S23); errors leave
  the stack once a later action succeeds (S20).
- **Narrow layout.** Search folds into a button, the account button shows one line, the
  record filter shrinks before its selects wrap (S52, S53).

Left different on purpose, with the reason, in [ui-spec.md §13](../ui-spec.md#13-deliberate-differences-from-the-real-console).

## Screenshots

| File | Status | Evidence | Notes |
|---|---|---|---|
| `S01-signin-user-type` | VERIFIED | side-by-side/S01-signin.png, difference 33.29 | Layout matched (logo, 340 px card at x 494, promo panel). Copy, user-type tiles and the legal links differ on purpose: the page must not pass for the real AWS sign-in (ui-spec §13). |
| `S03-account-menu-open` | VERIFIED | side-by-side/S03-account-menu-open.png, difference 5.31 | Menu rebuilt from the captured markup: account name, summary, Switch project, Projects, Team, Billing, Profile, Language, Visual mode, Sign out. Mocked entries say so when chosen. |
| `S04-dashboard` | VERIFIED | side-by-side/S04-dashboard.png, difference 7.77 | Placeholder by assignment: the frame, breadcrumb and active link match; the content is "Coming soon". |
| `S05-side-navigation-open` | INSPECTED | viewed; no dedicated clone capture | Same groups, order, "New" markers and external links; compared through S10. |
| `S06-split-panel-closed` | INSPECTED | viewed; no dedicated clone capture | Collapsed split panel trigger in the toolbar; stock Cloudscape, exercised in e2e. |
| `S07-help-panel-open` | VERIFIED | side-by-side/S07-help-panel-open.png, difference 9.12 |  |
| `S07-help-panel-zone-details` | INSPECTED | viewed; no dedicated clone capture | Help panel on the zone page; same component as S07-help-panel-open. |
| `S08-services-menu-open` | VERIFIED | side-by-side/S08-services-menu-open.png, difference 6.45 |  |
| `S08-support-menu-open` | VERIFIED | side-by-side/S08-support-menu-open.png, difference 10.91 |  |
| `S08-top-search-focused` | VERIFIED | side-by-side/S08-top-search-focused.png, difference 5.78 |  |
| `S09-visual-mode-menu` | INSPECTED | viewed; no dedicated clone capture | Three visual-mode buttons (browser default, light, dark) with the console's icons; e2e checks persistence. |
| `S10-focus-ring-table` | INSPECTED | viewed; no dedicated clone capture | Keyboard focus ring and descending sort on a column header; stock Cloudscape. |
| `S10-hosted-zones-column-menu` | INSPECTED | viewed; no dedicated clone capture | Row selected with a column header focused; stock Cloudscape. |
| `S10-hosted-zones-list` | VERIFIED | side-by-side/S10-hosted-zones-list.png, difference 2.91 |  |
| `S10-hosted-zones-sorted` | INSPECTED | viewed; no dedicated clone capture | Sort by name is plain alphabetical on click (API changed to match: `sort=name`); the unsorted order stays Route 53's. |
| `S11-hosted-zones-row-selected` | VERIFIED | side-by-side/S11-hosted-zones-row-selected.png, difference 4.63 |  |
| `S12-hosted-zones-filter-operators` | VERIFIED | side-by-side/S12-hosted-zones-filter-operators.png, difference 5.85 |  |
| `S12-hosted-zones-filter-properties` | VERIFIED | side-by-side/S12-hosted-zones-filter-properties.png, difference 5.7 |  |
| `S12-hosted-zones-filter-values` | INSPECTED | viewed; no dedicated clone capture | Operator typed by hand ("Hosted zone name : ="); free-text entry works the same way. |
| `S13-hosted-zones-filter-token` | VERIFIED | side-by-side/S13-hosted-zones-filter-token.png, difference 4.97 |  |
| `S13-hosted-zones-two-tokens` | INSPECTED | viewed; no dedicated clone capture | Two tokens with the and/or selector, "0 matches", header still counting all zones; fixed (the header used to show the filtered count). |
| `S14-hosted-zones-no-match` | VERIFIED | side-by-side/S14-hosted-zones-no-match.png, difference 5.26 |  |
| `S15-hosted-zones-preferences-modal` | VERIFIED | side-by-side/S15-hosted-zones-preferences-modal.png, difference 2.84 |  |
| `S16-hosted-zones-empty` | VERIFIED | side-by-side/S16-hosted-zones-empty.png, difference 2.88 |  |
| `S17-create-hosted-zone-fullpage` | INSPECTED | viewed; no dedicated clone capture | Same state as S17-create-hosted-zone-top. |
| `S17-create-hosted-zone-top` | VERIFIED | side-by-side/S17-create-hosted-zone-top.png, difference 3.21 |  |
| `S18-create-hosted-zone-filled` | INSPECTED | viewed; no dedicated clone capture | Filled form with two tags; same components as S18-create-hosted-zone-tag-row. |
| `S18-create-hosted-zone-private` | VERIFIED | side-by-side/S18-create-hosted-zone-private.png, difference 5.88 |  |
| `S18-create-hosted-zone-tag-row` | VERIFIED | side-by-side/S18-create-hosted-zone-tag-row.png, difference 3.96 |  |
| `S19-create-hosted-zone-error-empty` | VERIFIED | side-by-side/S19-create-hosted-zone-error-empty.png, difference 3.55 |  |
| `S19-create-hosted-zone-error-invalid` | VERIFIED | side-by-side/S19-create-hosted-zone-error-invalid.png, difference 4.31 |  |
| `S20-hosted-zone-created` | VERIFIED | side-by-side/S20-hosted-zone-created.png, difference 5.87 |  |
| `S21-edit-hosted-zone` | VERIFIED | side-by-side/S21-edit-hosted-zone.png, difference 3.25 |  |
| `S22-delete-empty-hosted-zone-modal` | INSPECTED | viewed; no dedicated clone capture | Empty zone: no warning box. Same modal as S22-delete-hosted-zone-modal. |
| `S22-delete-hosted-zone-modal` | VERIFIED | side-by-side/S22-delete-hosted-zone-modal.png, difference 5.13 |  |
| `S22-delete-hosted-zone-modal-confirmed` | INSPECTED | viewed; no dedicated clone capture | Delete enabled once "delete" is typed; covered by e2e. |
| `S22-delete-zone-from-details-modal` | INSPECTED | viewed; no dedicated clone capture | Same modal opened from the zone page; covered by e2e. |
| `S22-hosted-zone-deleted-notification` | INSPECTED | viewed; no dedicated clone capture | Green flash "Hosted zone … was successfully deleted." and "0 hosted zone selected"; wording fixed to the singular. |
| `S22-zone-deleted-from-details` | INSPECTED | viewed; no dedicated clone capture | Deleting from the zone page returns to the list with the flash; covered by e2e. |
| `S23-delete-hosted-zone-blocked` | VERIFIED | side-by-side/S23-delete-hosted-zone-blocked.png, difference 4.8 |  |
| `S24-zone-details-collapsed` | VERIFIED | side-by-side/S24-zone-details-collapsed.png, difference 6.96 |  |
| `S25-zone-details-expanded` | VERIFIED | side-by-side/S25-zone-details-expanded.png, difference 8.99 |  |
| `S26-short-viewport-scrolled-bottom` | INSPECTED | viewed; no dedicated clone capture | 620 px viewport scrolled to the end; sticky table header and footer, stock Cloudscape. |
| `S26-short-viewport-scrolled-mid` | INSPECTED | viewed; no dedicated clone capture | As above, mid scroll. |
| `S26-zone-details-records-fullpage` | VERIFIED | side-by-side/S26-zone-details-records-fullpage.png, difference 8.5 |  |
| `S26-zone-details-scrolled` | INSPECTED | viewed; no dedicated clone capture | Zone page scrolled: toolbar and table header stick. |
| `S27-many-records-selected` | INSPECTED | viewed; no dedicated clone capture | "11 records selected", button reads "Delete records"; plural label added. |
| `S27-record-panel-copied-popover` | INSPECTED | viewed; no dedicated clone capture | "Copied" popover of the inline copy button; stock Cloudscape `CopyToClipboard`. |
| `S27-record-selected-panel` | VERIFIED | side-by-side/S27-record-selected-panel.png, difference 9.67 |  |
| `S27-split-panel-preferences` | INSPECTED | viewed; no dedicated clone capture | Split panel preferences (bottom / side); stock Cloudscape. |
| `S27-two-records-selected` | VERIFIED | side-by-side/S27-two-records-selected.png, difference 11.78 |  |
| `S28-records-filter-focused` | INSPECTED | viewed; no dedicated clone capture | Ten filter properties; Differentiator and Evaluate target health were missing and were added (API and UI). |
| `S28-records-filter-typing` | INSPECTED | viewed; no dedicated clone capture | "Use: www" free-text suggestion; stock Cloudscape. |
| `S28-records-filtered-by-type` | INSPECTED | viewed; no dedicated clone capture | Type select adds a `Type = A` token; match count repeated after the selects (added). |
| `S28-records-filtered-text` | VERIFIED | side-by-side/S28-records-filtered-text.png, difference 16.12 |  |
| `S28-records-no-match` | INSPECTED | viewed; no dedicated clone capture | No matches state with two tokens. |
| `S28-records-type-filter-open` | VERIFIED | side-by-side/S28-records-type-filter-open.png, difference 9.52 |  |
| `S29-records-preferences-modal` | VERIFIED | side-by-side/S29-records-preferences-modal.png, difference 3.66 |  |
| `S30-manage-tags` | INSPECTED | viewed; no dedicated clone capture | Manage tags opens the edit page; compared through S21. |
| `S30-zone-tags-tab` | VERIFIED | side-by-side/S30-zone-tags-tab.png, difference 3.95 |  |
| `S31-accelerated-recovery-tab` | VERIFIED | side-by-side/S31-accelerated-recovery-tab.png, difference 4.12 |  |
| `S31-dnssec-tab` | VERIFIED | side-by-side/S31-dnssec-tab.png, difference 6.67 |  |
| `S32-create-record-quick-create` | VERIFIED | side-by-side/S32-create-record-quick-create.png, difference 5.2 |  |
| `S33-create-record-type-dropdown` | VERIFIED | side-by-side/S33-create-record-type-dropdown.png, difference 9.02 | All 16 types listed in the console's order; the seven the clone does not store are disabled. |
| `S34-create-record-routing-dropdown` | VERIFIED | side-by-side/S34-create-record-routing-dropdown.png, difference 7.13 | Eight policies listed; IP-based and Geoproximity are disabled. |
| `S35-create-record-alias-endpoints` | INSPECTED | viewed; no dedicated clone capture | "Choose endpoint" list of 14 alias targets; rebuilt. Only "another record in this hosted zone" is resolved by the clone; the others take the target's DNS name and hosted zone ID by hand. |
| `S35-create-record-alias-on` | VERIFIED | side-by-side/S35-create-record-alias-on.png, difference 5.93 |  |
| `S36-create-record-two-records` | VERIFIED | side-by-side/S36-create-record-two-records.png, difference 6.55 |  |
| `S37-wizard-define-record` | VERIFIED | side-by-side/S37-wizard-define-record.png, difference 10.57 | The dialog reuses the quick-create fields; the console's longer field descriptions are not reproduced. |
| `S37-wizard-step-1` | VERIFIED | side-by-side/S37-wizard-step-1.png, difference 7.17 | Wizard implemented. Tiles carry no illustrations; IP-based and Geoproximity are listed but disabled. |
| `S37-wizard-step-2` | VERIFIED | side-by-side/S37-wizard-step-2.png, difference 2.39 |  |
| `S38-create-record-error-empty-ttl` | INSPECTED | viewed; no dedicated clone capture | Shows the in-progress flash "Creating record(s) for …" / "This can take a moment."; added. |
| `S38-create-record-error-empty-value` | VERIFIED | side-by-side/S38-create-record-error-empty-value.png, difference 4.57 |  |
| `S38-create-record-error-invalid-value` | VERIFIED | side-by-side/S38-create-record-error-invalid-value.png, difference 4.55 |  |
| `S39-notifications-stack-expanded` | INSPECTED | viewed; no dedicated clone capture | Actually the bell's panel: "Notifications", "Notification center", "No notifications"; rebuilt. |
| `S39-record-created-notification` | VERIFIED | side-by-side/S39-record-created-notification.png, difference 8.25 |  |
| `S40-edit-record` | VERIFIED | side-by-side/S40-edit-record.png, difference 12.37 |  |
| `S40-edit-record-saved-notification` | INSPECTED | viewed; no dedicated clone capture | Blue "… was successfully updated." flash with View status; covered by e2e. |
| `S41-delete-record-modal-many` | INSPECTED | viewed; no dedicated clone capture | Eleven records listed with search and pagination. |
| `S41-delete-record-modal-single` | VERIFIED | side-by-side/S41-delete-record-modal-single.png, difference 5.05 |  |
| `S41-delete-record-modal-two` | VERIFIED | side-by-side/S41-delete-record-modal-two.png, difference 5.72 |  |
| `S41-records-deleted-notification` | INSPECTED | viewed; no dedicated clone capture | Green "The records were successfully deleted." flash; covered by e2e. |
| `S42-import-zone-file` | VERIFIED | side-by-side/S42-import-zone-file.png, difference 4.52 |  |
| `S42-import-zone-file-invalid` | INSPECTED | viewed; no dedicated clone capture | Preview keeps listing what it could read. The clone also names the bad lines and disables Import (the console lets it fail on submit). |
| `S42-import-zone-file-preview` | VERIFIED | side-by-side/S42-import-zone-file-preview.png, difference 6.98 |  |
| `S42-import-zone-file-result` | INSPECTED | viewed; no dedicated clone capture | Blue "Records for … were successfully created." flash; covered by e2e. |
| `S44-health-checks` | VERIFIED | side-by-side/S44-health-checks.png, difference 4.47 | Placeholder by assignment; frame, breadcrumb and active link match. |
| `S45-traffic-policies` | VERIFIED | side-by-side/S45-traffic-policies.png, difference 3.5 | Placeholder by assignment. |
| `S46-resolver` | VERIFIED | side-by-side/S46-resolver.png, difference 128.18 | Placeholder by assignment. The reference itself is an access-denied page under a "Region unavailable" dialog. |
| `S47-profiles` | VERIFIED | side-by-side/S47-profiles.png, difference 127.88 | Placeholder by assignment. The reference itself is an access-denied page under a "Region unavailable" dialog. |
| `S48-dark-hosted-zones-list` | VERIFIED | side-by-side/S48-dark-hosted-zones-list.png, difference 4.91 |  |
| `S48-dark-hosted-zones-selected` | INSPECTED | viewed; no dedicated clone capture | Dark list with the details panel; same tokens as S48-dark-hosted-zones-list. |
| `S49-dark-edit-record` | INSPECTED | viewed; no dedicated clone capture | Dark edit panel. |
| `S49-dark-record-selected` | VERIFIED | side-by-side/S49-dark-record-selected.png, difference 8.15 |  |
| `S49-dark-zone-details` | INSPECTED | viewed; no dedicated clone capture | Dark zone page without a selection. |
| `S50-dark-create-hosted-zone` | INSPECTED | viewed; no dedicated clone capture | Dark create hosted zone. |
| `S50-dark-create-record` | VERIFIED | side-by-side/S50-dark-create-record.png, difference 5.75 |  |
| `S50-dark-create-record-error` | INSPECTED | viewed; no dedicated clone capture | Dark inline "Endpoints field is required to have value." error. |
| `S51-dark-delete-record-modal` | VERIFIED | side-by-side/S51-dark-delete-record-modal.png, difference 3.86 |  |
| `S51-dark-delete-zone-modal` | INSPECTED | viewed; no dedicated clone capture | Dark delete-zone modal with the warning box. |
| `S52-narrow-hosted-zones-list` | VERIFIED | side-by-side/S52-narrow-hosted-zones-list.png, difference 8.12 |  |
| `S52-narrow-navigation-open` | INSPECTED | viewed; no dedicated clone capture | 800 px with the navigation closed and the side split panel open. |
| `S53-narrow-create-record` | INSPECTED | viewed; no dedicated clone capture | Create record in a narrow window. |
| `S53-narrow-zone-details` | VERIFIED | side-by-side/S53-narrow-zone-details.png, difference 9.13 |  |
| `S53-narrow-zone-details-fullpage` | INSPECTED | viewed; no dedicated clone capture | Full page of S53. |
| `S53-zone-details-width-1300` | INSPECTED | viewed; no dedicated clone capture | 1300 px: filter row keeps its selects; the property filter shrinks first. |
| `S53-zone-details-width-688` | INSPECTED | viewed; no dedicated clone capture | 688 px: split panel moves to the bottom; search folds into a button. |
| `S53-zone-details-width-950` | INSPECTED | viewed; no dedicated clone capture | 950 px: actions wrap under the title. |

## Videos

All are 1920x966 at 30 fps. Frames were extracted with `reference/tools/extract_frames.py`
into `reference/frames/<video>/` (3x3 contact sheets at 6 fps and scene-change frames); the
sheets listed were read. "Verified" means the same flow runs in the end-to-end tests
(`frontend/e2e`).

| File | Length | Status | Sheets read | What it shows and how the clone compares |
|---|---|---|---|---|
| `V01-hosted-zones-hard-refresh` | 8.9 s | INSPECTED | 002 | Empty frame, then "Hosted zones (0)" with six skeleton rows, a disabled filter and a spinning refresh button, then the navigation and panel. The clone renders the frame on the server, so it has no blank phase; its loading table is the same skeleton. |
| `V02-zone-details-scroll` | 5.2 s | VERIFIED | 001 | Window scrolls; header, toolbar and table header stick. Same scroll model (snapshot diff: no inner scroll containers in either). |
| `V03-zone-details-scroll-short-viewport` | 7.4 s | VERIFIED | 003 | 620 px viewport: table header sticks under the toolbar, navigation and panel scroll on their own. Stock Cloudscape, same geometry. |
| `V04-nav-help-splitpanel` | 11.6 s | VERIFIED | 004, 007 | Navigation collapses, help panel opens next to the split panel, split panel closes to a toolbar trigger. Stock Cloudscape `AppLayoutToolbar`; exercised in e2e. |
| `V05-create-hosted-zone` | 16.8 s | VERIFIED | 006, 010, work/creating | Empty submit, tags, in-progress flash, green flash on the new zone with skeleton rows. In-progress flash added. |
| `V06-create-record` | 18.0 s | VERIFIED | 001 | Record name focused on arrival, type dropdown, alias toggle, add and remove a record. Focus and Delete button fixed. |
| `V07-edit-record-and-bulk-delete` | 16.2 s | VERIFIED | 008, work/creating-record | Edit in the side panel, blue flash, select two, delete dialog. |
| `V08-delete-hosted-zone` | 21.3 s | VERIFIED | 002, 004, work/deleting | Blocked delete (red flash), then a successful one (green flash, back on the list). |
| `V09-filter-sort` | 15.9 s | VERIFIED | 010 | Property, value, tokens, clear, sort by name. Property-to-value step and alphabetical name sort fixed. |
| `V10-hover-and-focus` | 16.1 s | INSPECTED | 006 | Hover and focus rings on buttons, rows, links, tabs. Stock Cloudscape; the header's own buttons use the same 2 px `#42b4ff` ring. Not asserted by a test. |
| `V11-expand-tabs-copy` | 19.4 s | VERIFIED | 009 | Expand "Hosted zone details", switch tabs with the keyboard, copy button. |
| `V12-responsive-resize` | 14.5 s | INSPECTED | 004 | Window dragged narrow and back. Compared at 800 px through S52 and S53; widths in between were not captured from the clone. |

## DOM snapshots

Every snapshot's `visibleText` was compared with the clone (`copycheck`): the lines of
copy that never appear in the clone are listed. Data (names, IDs, counts) is excluded.
`© 2026, Amazon Web Services, Inc. or its affiliates.` is missing everywhere on purpose.

| File | Status | Lines of copy | Missing from the clone |
|---|---|---|---|
| `D00-hosted-zones-empty` | VERIFIED | 50 | none |
| `D01-hosted-zones-list` | VERIFIED | 50 | none. Also the source of the text widths used to choose the typeface, and of the header and footer positions. |
| `D02-hosted-zones-filter-dropdown` | VERIFIED | 56 | none ("Accelerated recovery" property added) |
| `D03-hosted-zones-preferences-modal` | VERIFIED | 73 | none |
| `D04-zone-details-top` | VERIFIED | 37 | none |
| `D05-zone-details-scrolled` | VERIFIED | 61 | none |
| `D06-record-selected-panel` | VERIFIED | 40 | none. Split panel 400 px wide at top 90 px, as in the clone. |
| `D07-create-hosted-zone` | VERIFIED | 33 | none |
| `D08-create-record-type-dropdown-open` | VERIFIED | 51 | none (the seven extra record types were added) |
| `D09-delete-record-modal` | VERIFIED | 41 | none ("Delete records" added) |
| `D09b-delete-hosted-zone-modal` | VERIFIED | 60 | none |
| `D10-after-success-notification` | VERIFIED | 62 | none |
| `D10b-after-delete-notification` | VERIFIED | 40 | none |
| `D11b-help-panel-open` | VERIFIED | 42 | "Was this content helpful?" with Yes and No. The help text itself was replaced with the console's. |
| `D12-hosted-zones-list-dark` | VERIFIED | 52 | none |
| `D12b-zone-details-dark` | VERIFIED | 61 | none |
| `D13-signin` | VERIFIED | 16 | 14 of 16, on purpose: user-type tiles, "Next", "New to AWS? Sign up", the AWS legal text. |
| `D14-import-zone-file` | VERIFIED | 25 | none |
| `D15-hosted-zones-list-narrow` | VERIFIED | 51 | none |
| `raw/hosted-zones-header.html` | INSPECTED | - | Source of the logo and icon shapes, the services, help and account menus. |
| `raw/hosted-zones-footer.html` | INSPECTED | - | Source of the footer's items and icons. |
| `raw/hosted-zones-nav.html`, `raw/hosted-zones-main.html` | INSPECTED | - | Read for structure only. |

Snapshot diff against the clone (`snapshot-diff.mjs`, D01, D04 and D12):

| Check | Result |
|---|---|
| Design tokens | 599 tokens exist under the same name in both; all have the same value in light and in dark mode (two differ only in notation, `#0099ff` against `#09f`). |
| Sticky and fixed elements | Same boxes: header 1920x48 at 0, toolbar 1920x42 at 48, navigation 280x955 at 90, table header at top 102, footer 1920x35 at 1045. The clone's header and footer are `sticky` where the console's are `fixed`; the table header block is 148 px against 147. |
| Scroll model | The window scrolls in both; neither has an inner scroll container. |
| Motion | Cloudscape's transitions are the same. The console's extra entries belong to its own navigation widgets; the clone's to Next.js and the header menus. |

## Notes and tools

| File | Status | Use |
|---|---|---|
| `NOTES.md` | INSPECTED | Viewport 1920x1080 at DPR 1; narrow shots at 800 px; V03 at 1920x620; what was not captured. |
| `CAPTURE_GUIDE.md` | INSPECTED | What each ID is meant to show. |
| `tools/extract_frames.py` | INSPECTED | Produced `reference/frames/`. |
| `tools/aws-ui-snapshot.js` | INSPECTED | Run inside the clone by `snapshot-diff.mjs`. |

## Known gaps in the evidence

- 47 screenshots have no clone capture of their own. Each is a variation of a verified
  state (another row selected, dark mode of a verified page, a different width) or a page
  that is a placeholder by assignment; the table says which.
- S01 was captured at a different zoom from the rest (its text is 1.25 times larger), so its
  difference value is not comparable; the layout was checked against D13's coordinates.
- Hover states (V10) and the widths between 800 and 1920 px (V12) were looked at in the
  reference but not captured from the clone.
- Nothing here measures animation timing frame by frame; motion is inherited from the
  same Cloudscape components and was compared as CSS declarations only.
