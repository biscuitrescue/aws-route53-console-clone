# UI specification

Derived from captures of the real Route 53 console taken on 2026-10-09 at 1920x1080, DPR 1:
screenshots (`S##`), screen recordings (`V##`) and DevTools snapshots (`D##`). Each item
cites the capture it comes from. The captures themselves are private and not in the
repository.

## 1. Findings that changed the plan

| Expected | Real console | Source |
|---|---|---|
| Blue Cloudscape primary buttons | Primary buttons are orange `#ff9900` (hover and active `#fa6f00`) with dark text `#0f141a`. Every other colour token is stock Cloudscape visual refresh. | D01 `cssVariables`, S10 |
| Cloudscape `TopNavigation` | A custom 48 px header (`#161d26`): logo, Amazon Q button, services grid, search with `[Alt+S]` hint, CloudShell, notifications bell, help, account name. No region selector and no settings gear. | S10, D01 `stickyAndFixed`, `raw/hosted-zones-header.html` |
| Breadcrumbs above the content | A sticky 42 px toolbar under the header holds the navigation trigger, breadcrumbs, split-panel trigger and help trigger (Cloudscape `AppLayoutToolbar`). | D01 `stickyAndFixed`, S10 |
| No footer | A fixed 35 px footer (`#161d26`): CloudShell, Agent Toolkit for AWS, Feedback, Language, copyright, Privacy, Terms, Cookie preferences. | S10, D01 |
| Bottom split panel for record details | A **side** split panel, open by default on both the zones list and the zone details page. Editing a record happens inside it. | S11, S27, S40, D06 |
| Multi-select zones table | Zones are **single-select** (radio); records are multi-select (checkbox). | S11, S27 |
| Filter placeholder "Filter hosted zones…" | Both tables use `Filter records by property or value`, under the line "Automatic mode is the current search behavior optimized for best filter results. To change modes go to settings." | S10, S26 |
| Success flash after creating a record | Record changes show a **blue info** flash with a "View status" button; zone create/delete show green success flashes. | S39, S20, S22 |
| Inline error for an invalid name | Server-side rejections appear as a red flash "Error occurred / Please try again later. / (detail)". Only "required" checks are inline. | S19, S38 |
| Settings panel for visual mode | Visual mode (browser default / light / dark) is three icon buttons in the account menu. | S03 |
| Hash-less URLs | The console uses hash routes: `#CreateHostedZone`, `#ListRecordSets/{id}`, `#EditHostedZone/{id}`, `#CreateRecordSet/{id}`, `#ImportZoneFileRecordSets/{id}`. | D07, D04, D14 |
| Tabs: Records, DNSSEC signing, Hosted zone tags | Records (n), **Accelerated recovery**, DNSSEC signing, Hosted zone tags (n). | S24 |
| Side nav as in the brief | See section 3; the groups are Global Resolver, VPC Resolver, Domains, IP-based routing, Traffic flow. | S05 |

## 2. Global frame

**Scroll model (D01, D04, D05, V03).** The window scrolls; there is no inner scroll container.
Fixed: header (top 0, 48 px, z 1003) and footer (bottom 0, 35 px). Sticky: toolbar (top 48 px,
42 px), navigation (top 90 px, 280 px wide), side split panel (top 90 px, 400 px wide), the
table's header block (top 90 px, `stickyHeader`), and the table's sticky horizontal scrollbar.

**Typography (D01, D04).** `"Amazon Ember", "Helvetica Neue", Roboto, Arial, sans-serif`,
14 px / 20 px body. h1 24/30, h2 20/24 bold, tabs 16/20 bold, table header 14 px bold.
Amazon Ember is proprietary; the clone uses Cloudscape's default Open Sans stack.

**Motion (D10 `motion`, V04–V11).** All motion is stock Cloudscape: 135 ms
`cubic-bezier(0.165, 0.84, 0.44, 1)` icon rotations, 115 ms modal fade and scale-in,
135 ms dropdown fade, 165 ms navigation and link transitions, 115 ms flash transitions.
Nothing custom, so the clone inherits it by using the same components.

**Header (S10, S03, S08).** Left: logo, Amazon Q button, services grid button, search field
(540 px, placeholder "Search", hint `[Alt+S]`). Right: CloudShell, bell, help (menu), account
button showing the account name with the user name beneath it. Account menu: account name,
plan status, Switch project, Projects, Team, Billing, Profile, Language, Visual mode
(three icons), "Sign out of {account}". `Alt+S` focuses search.

**Footer (S10).** Left: CloudShell, Agent Toolkit for AWS, Feedback, Language. Right:
copyright, Privacy, Terms, Cookie preferences.

**Notifications (S20, S39, S41, D10).** Cloudscape `Flashbar` with `stackItems`. With more
than one flash a "Notifications" bar shows counts per type and expands the stack.

**Help panel (S07).** The toolbar's info button and every "Info" link open the tools
drawer with a title, body text and a "Learn more" footer.

**Page titles.** `Hosted zones | Route 53 | {account}`, `{zone} - details | {account}`,
`{zone} - add record | {account}`, `{zone} - edit | {account}`.

## 3. Side navigation (S05, S10)

Header "Route 53". Links: Dashboard, Hosted zones, Health checks, Profiles. Expandable
groups (expanded by default): **Global Resolver** (Global resolvers `New`, Shared DNS views
`New`), **VPC Resolver** (VPCs, Inbound endpoints, Outbound endpoints, Rules, Query logging,
Outposts), **Domains** (Registered domains, Requests), **IP-based routing** (CIDR
collections), **Traffic flow** (Traffic policies, Policy records). Divider. External links:
DNS Firewall, Application Recovery Controller.

Navigation is open on list pages and closed on form pages (S17, S32). Everything except
Hosted zones leads to a "Coming soon" page inside the frame with the right breadcrumb and
active link (S04, S44–S47 show the real pages those replace).

## 4. Hosted zones list (S10–S16, D01–D03, V01, V09)

- Breadcrumbs: Route 53 > Hosted zones.
- Header `Hosted zones (n)`, or `(1/n)` with a selection. Actions: refresh icon button,
  View details, Edit, Delete (all three disabled without a selection), Create hosted zone
  (primary).
- Description line and filter as in section 1. Pagination and a preferences gear on the right.
- Columns (all sortable): Hosted zone name (link), Type (`Public`/`Private`), Created by
  (`Route 53`), Record count, Description (`-` when empty), Hosted zone ID. Accelerated
  recovery is an optional hidden column. Names are shown without the trailing dot.
- Default order: by domain, parent before child (S10: `r53clone-demo.com`,
  `api.r53clone-demo.com`, `example-shop.net`).
- Filter properties: Hosted zone name, Type, Created by, Record count, Description, Hosted
  zone ID. Choosing a property inserts `Hosted zone name : ` (contains is the default
  operator). Tokens read `Hosted zone name : shop`; with several, an `and`/`or` selector
  appears between them, plus "n matches" and "Clear filters" (S12, S13).
- Empty: **No hosted zones** / "There are no hosted zones created for this account." /
  Create hosted zone button (S16). No match: **No matches** / "No results match your
  query." / Clear filters (S14).
- Loading: skeleton rows (V01).
- Preferences modal (S15): Page size 10/30/50/100, Wrap lines, Search mode
  (Automatic/Full/Fast), Select visible columns. Buttons Cancel, Confirm.
- Selecting a row fills the side split panel "Hosted zone details": Hosted zone name, Hosted
  zone ID, Description, Query log, Type, Record count, Name servers (bulleted) (S11).
  With nothing selected the panel reads "0 hosted zones selected" in the same style as S24.

## 5. Create hosted zone (S17–S20, D07, V05)

- Breadcrumbs: Route 53 > Hosted zones > Create hosted zone. Navigation closed.
- Header "Create hosted zone" + Info.
- Container **Hosted zone configuration** with description. Fields:
  - **Domain name** + Info; description "This is the name of the domain that you want to
    route traffic for."; placeholder `example.com`; constraint
    ``Valid characters: a-z, 0-9, ! " # $ % & ' ( ) * + , - / : ; < = > ? @ [ \ ] ^ _ ` { | } . ~``.
  - **Description - optional** + Info; "This value lets you distinguish hosted zones that
    have the same name."; textarea placeholder "The hosted zone is used for..."; constraint
    "The description can have up to 256 characters. n/256".
  - **Type** + Info; tiles **Public hosted zone** / **Private hosted zone** with their
    descriptions. Private adds a container "VPCs to associate with the hosted zone" with
    Region and VPC ID selects, Remove VPC, Add VPC (S18).
- Container **Tags** + Info: "Apply tags to hosted zones to help organize and identify
  them."; "No tags associated with the resource."; Add tag; "You can add up to 50 more
  tags."; rows Key / Value - optional / Remove tag (Cloudscape `TagEditor`).
- Footer: Cancel (link), Create hosted zone (primary).
- Empty submit: inline "Domain name is empty." (S19). Invalid name: red flash "Error
  occurred" / "Please try again later." / `(DomainLabelEmpty (Domain label is empty)
  encountered with 'bad..name')`.
- Success: navigates to the zone with a green flash "**{zone} was successfully created.**
  Now you can create records in the hosted zone to specify how you want Route 53 to route
  traffic for your domain." (S20)

## 6. Hosted zone details (S24–S31, D04–D06, V02, V03, V11)

- Breadcrumbs: Route 53 > Hosted zones > {zone}.
- Header: `Public`/`Private` badge, zone name, Info. Actions: Delete zone, Test record,
  Configure query logging.
- Expandable container **Hosted zone details** (collapsed by default) with an "Edit hosted
  zone" button in its header. Expanded: Hosted zone name, Hosted zone ID, Description,
  Query log, Type ("Public hosted zone"), Record count, Name servers (S25).
- Tabs: Records (n), Accelerated recovery, DNSSEC signing, Hosted zone tags (n).
- **Records table** (S26): header `Records (n)` + Info, or `(k/n)` with a selection;
  actions refresh, Delete record (disabled without a selection), Import zone file, Create
  record (primary). Filter line as in section 1, then three selects: Type, Routing policy,
  Alias. Columns: Record name, Type, Routing policy, Differentiator, Alias,
  Value/Route traffic to (one value per line), TTL (seconds) (thousands separator), Health
  check ID, Evaluate target health, Record ID. Empty cells show `-`. Routing policy
  `Simple`, Alias `Yes`/`No`. Multi-select.
- Order: by name, parent before child, then type (S26).
- Filter properties: all ten columns. Free text matches names and values (S28: `www` also
  matches the PTR and CNAME that point at it). Type select options: A, AAAA, CNAME, MX,
  TXT, PTR, SRV, SPF, NAPTR, CAA, NS, SOA, DS, TLSA, SSHFP, HTTPS, SVCB. Routing policy
  options: Simple, Weighted, Geolocation, Latency, Failover, Multivalue answer, IP-based,
  Geoproximity location. Alias options: Alias, Non-alias. A select adds a token such as
  `Type = A`.
- Preferences modal as on the zones list, with the record columns (S29).
- **Side split panel** (S24, S27): "0 records selected" / "Select a record to see its
  details"; one record: "Record details", Edit record button, then Record name (copy),
  Record type, Value (copy), Alias, TTL (seconds), Routing policy; several: "n records
  selected". Split panel preferences: bottom or side.
- **Edit record** (S40, V07): the panel becomes "Edit record" with the same fields as
  quick create, then Cancel and Save. Success: blue flash "**{name} was successfully
  updated.**" + propagation text + View status.
- **Delete record(s)** (S41): modal "Delete selected record?" / "Delete n selected
  records?"; "Delete the record(s) permanently? This action cannot be undone. Your domain
  might become unavailable on the internet."; a small table (search, pagination, Record
  name, Type, Value/Route traffic to); Cancel, Delete. Success: green flash "The records
  were successfully deleted."
- **Hosted zone tags** tab (S30): container "Tags" with Manage tags button and a Key/Value
  table. Manage tags opens the edit page.
- **DNSSEC signing** and **Accelerated recovery** tabs (S31): status containers; in the
  clone these are informational with their actions marked coming soon.

## 7. Edit hosted zone (S21)

Breadcrumbs Route 53 > Hosted zones > {zone} > Edit. Header "Edit {zone}" + Info. Container
**Edit hosted zone**: read-only Domain name, Hosted zone ID, Record count, Type; editable
Description - optional (with counter). Container **Tags** as on create. Footer: Cancel,
Save changes.

## 8. Delete hosted zone (S22, S23, V08)

Modal "Delete hosted zone {zone}?" with the same warning sentence as record delete. When the
zone has records beyond NS and SOA, a warning box: "**Take these actions to delete hosted
zone {zone}**" / "Complete the following steps to successfully delete this hosted zone. If
you don't complete the steps, the deletion might be blocked by Route 53 service
validation." / bullet "Delete all records in this hosted zone, except the default NS and
SOA records." / button "Go to hosted zone details". Then "To confirm that you want to delete
the hosted zone, enter *delete* in the field." with placeholder `delete`. Delete is
disabled until the text matches. Blocked: red flash with
`(The specified hosted zone contains non-required resource record sets and so cannot be
deleted.)`. Success: green flash "Hosted zone {zone} was successfully deleted."

## 9. Create record (S32–S39, D08, V06)

- Breadcrumbs: Route 53 > Hosted zones > {zone} > Create record. Navigation closed.
- Expandable **Record creation method** (expanded): two columns, "Quick create (recommended
  for expert users)" and "Wizard (recommended for new users)" with their sentences.
- Header "Create record" + Info. Container **Quick create record** with a "Switch to
  wizard" link. Each record is an expandable "Record n" with a Delete button (disabled when
  it is the only one):
  - **Record name** + Info: input placeholder `subdomain`, the zone name after it;
    constraint "Keep blank to create a record for the root domain."
  - **Record type** + Info: select with descriptions, e.g. "A – Routes traffic to an IPv4
    address and some AWS resources" (full list in S33).
  - **Alias** toggle. Off: **Value** + Info, textarea with a type-specific placeholder
    (`192.0.2.235` for A), constraint "Enter multiple values on separate lines."; **TTL
    (seconds)** + Info, number input default 300, buttons 1m / 1h / 1d, constraint
    "Recommended values: 60 to 172800 (two days)". On: **Route traffic to** + Info with
    "Choose endpoint" and "Choose Region" selects (S35).
  - **Routing policy** + Info: Simple routing, Weighted, Geolocation, Latency, Failover,
    Multivalue answer, IP-based, Geoproximity (S34).
- Container footer: Add another record. Page footer: Cancel, Create records.
- Expandable **View existing records**: "The following table lists the existing records in
  {zone}."
- Empty value: inline "Endpoints field is required to have value." (S38). Invalid value: red
  flash with `(ARRDATAIllegalIPv4Address (Value is not a valid IPv4 address) encountered
  with '999.1.1.1'')`.
- Success: back on the zone with a blue flash "**{name} was successfully created.**" /
  "Route 53 propagates your changes to all of the Route 53 authoritative DNS servers within
  60 seconds. Use "View status" button to check propagation status." + View status (S39).
- **Wizard** (S37): step 1 "Choose routing policy" (tiles), step 2 "Configure records"
  with a table and a "Define simple record" modal.

## 10. Import zone file (S42, D14)

Breadcrumbs end in "Import zone file". Header + Info; "You can create records for a Route
53 hosted zone by importing a zone file." Field **Zone file**: "Paste the contents of your
zone file below."; textarea; constraint "If the hosted zone already contains records that
appear in the zone file, the import process fails, and no records are created. Enter
multiple records on separate lines." Table **Record preview for {zone} (n)** with "Route 53
creates the following records when you choose Import zone file. If you edit the contents of
the zone file above, the table reflects your changes."; columns Record name, Type,
Value/Route traffic to, TTL (seconds); empty text "This table displays records based on the
contents of your zone file." Footer: Cancel, Import. Success: blue flash "**Records for
{zone} were successfully created.**" + propagation text.

## 11. Sign-in (S01, D13)

Background `#fafafa`, centred logo, card "Sign In": "Access your AWS account by user
type.", tiles Root user / IAM user, Email address, Next (orange, full width), divider "OR",
"New to AWS? Sign up". A promotional panel sits to the right; legal text below the card.

## 12. Dark mode and narrow layout (S48–S53, D12, V12)

Dark is Cloudscape's dark mode (`#161d26` surfaces, `#c6c6cd` text); primary buttons stay
orange. Below about 690 px the navigation becomes an overlay and the toolbar keeps the
triggers; the table scrolls horizontally with the sticky scrollbar (S52, S53).

## 13. Deliberate differences from the real console

| Difference | Reason |
|---|---|
| Path routes (`/route53/v2/hostedzones/{id}`) instead of hash routes; the console's hash URLs redirect to them. | Server-side route guard and deep links need real paths. |
| Open Sans instead of Amazon Ember. | Amazon Ember is not licensed for reuse. |
| An approximated logo, a "demo clone" notice on the sign-in page and in the footer, and no AWS copyright line. | A public look-alike of the AWS sign-in page must not be mistakable for the real one. |
| Sign-in is one card with email and password and shows the demo credentials. | Authentication is mocked. |
| Record types limited to the nine in the assignment plus SOA; routing policies limited to those the API implements. | Assignment scope. |
| Filtering, sorting and pagination run in the API, not in the browser. | Assignment asks for a backend API; the visible behaviour is the same. |
| Extra actions on the zone page (Export zone, keyboard shortcuts help) and a "Replace existing records" option on import. | Bonus features the real console lacks. |
| Test record, Configure query logging, DNSSEC, Accelerated recovery, the wizard, alias endpoints for AWS resources: present but inert or "coming soon". | Outside the assignment scope. |
| The search-mode preference is shown but has no effect. | The API always searches every field. |

## 14. Verification against the references

Screenshots of the clone were taken in the same states as the references (same data,
1920x1080, light, dark and 800 px) and compared side by side. The same DevTools snapshot
script that produced the `D##` files was also run inside the clone and diffed:

| Check | Result |
|---|---|
| Design tokens (D01, D04, D12 `cssVariables`) | All 599 Cloudscape tokens the two share by name have the same value in light and in dark mode, once colour notation is normalised (`#fff` vs `#ffffff`). The console defines extra tokens for components the clone does not use. |
| Frame geometry (`stickyAndFixed`) | Identical: header 1920x48 at 0, toolbar 1920x42 at 48, navigation 280x955 at 90, side split panel 400x955 at x 1520, sticky table header at top 90 (zone page) and 102 (zones list), sticky table scrollbar, footer 1920x35 at 1045. The table header block is 1 px taller in the clone because of the font. |
| Scroll model (`windowScroll`, `scrollContainers`) | Same: the window scrolls, no inner scroll containers. |
| Motion (`motion`) | Every Cloudscape transition and animation present on the page is identical in property, duration and easing. The console's extra entries belong to its global navigation widgets (search, assistant) and to its always-mounted modal. |
| Copy | Headings, labels, placeholders, constraint and error text, empty states and notifications match the captured `visibleText`, except where section 13 says otherwise. |
| Flows (V05–V09) | Create zone, create/edit/delete records, blocked and successful zone delete, filtering and sorting behave as recorded; covered by the end-to-end test. |

Remaining visible differences are the deliberate ones in section 13, plus: glyph widths
(Open Sans is slightly wider than Amazon Ember), no sort control on the Differentiator and
Value columns (the API does not sort by them), and the navigation staying open at 800 px.

## 15. Open questions

- The password step of the real sign-in (S02) and the visual-mode transition (V14) were not
  captured; both follow stock Cloudscape.
- The private zone flow was captured only as a form state, not submitted.
