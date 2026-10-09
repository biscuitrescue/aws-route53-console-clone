import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { recordTypeInfo } from "../lib/record-types";
import type { RecordType } from "../lib/api/types";

const EMAIL = process.env.E2E_EMAIL ?? "demo@example.com";
const PASSWORD = process.env.E2E_PASSWORD ?? "Route53Demo!";

/** A zone name no other run uses, so the test can run against a shared deployment. */
const ZONE = `e2e-${Date.now().toString(36)}.example`;

const RECORDS: { name: string; type: RecordType; value: string }[] = [
  { name: "www", type: "A", value: "192.0.2.10" },
  { name: "www", type: "AAAA", value: "2001:db8::10" },
  { name: "blog", type: "CNAME", value: `www.${ZONE}` },
  { name: "", type: "TXT", value: '"v=spf1 -all"' },
  { name: "", type: "MX", value: `10 mail.${ZONE}` },
  { name: "sub", type: "NS", value: "ns-1.example.net" },
  { name: "10", type: "PTR", value: `www.${ZONE}` },
  { name: "_sip._tcp", type: "SRV", value: `10 60 5060 sip.${ZONE}` },
  { name: "", type: "CAA", value: '0 issue "amazon.com"' },
  { name: "", type: "SPF", value: '"v=spf1 -all"' },
  { name: "sip", type: "NAPTR", value: '100 10 "u" "sip+E2U" "!^.*$!sip:info@example.com!i" .' },
  { name: "child", type: "DS", value: `12345 13 2 ${"ab".repeat(32)}` },
  { name: "_443._tcp.www", type: "TLSA", value: `3 1 1 ${"cd".repeat(32)}` },
  { name: "host", type: "SSHFP", value: `4 2 ${"ef".repeat(32)}` },
  { name: "", type: "HTTPS", value: '1 . alpn="h3,h2" ipv4hint="192.0.2.10"' },
  { name: "_dns", type: "SVCB", value: "1 doh.example.net. alpn=h2 port=443" },
];

/** The zone's own NS and SOA plus one record of every type. */
const ALL_RECORDS = RECORDS.length + 2;

async function signIn(page: Page) {
  await page.getByLabel("Email address").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/route53\/v2\//);
}

/** The flashbar; with several notifications it shows the newest on top. */
const flash = (page: Page) => page.getByRole("list", { name: "Notifications" });

test("sign in, manage a zone and its records, sign out", async ({ page }) => {
  // The route guard sends an anonymous visitor to sign-in and back after login.
  await page.goto("/route53/v2/hostedzones");
  await expect(page).toHaveURL(/\/signin\?redirect=/);
  await signIn(page);
  await expect(page).toHaveURL(/\/route53\/v2\/hostedzones$/);
  await expect(page.getByRole("heading", { name: /Hosted zones/ })).toBeVisible();

  // Create a hosted zone: validation first, then the real thing.
  // Buttons that navigate are links, so they can be opened in a new tab.
  await page.getByRole("link", { name: "Create hosted zone" }).first().click();
  await page.getByRole("button", { name: "Create hosted zone", exact: true }).click();
  await expect(page.getByText("Domain name is empty.")).toBeVisible();
  await page.getByPlaceholder("example.com").fill(ZONE);
  await page
    .getByPlaceholder("The hosted zone is used for...")
    .fill("Created by the end-to-end test");
  await page.getByRole("button", { name: "Create hosted zone", exact: true }).click();
  await expect(flash(page)).toContainText(`${ZONE} was successfully created.`);
  await expect(page.getByRole("tab", { name: "Records (2)" })).toBeVisible();
  const zoneUrl = page.url();

  // One record of every supported type, in a single quick-create batch.
  await page.getByRole("link", { name: "Create record" }).click();
  for (const [index, record] of RECORDS.entries()) {
    if (index > 0) await page.getByRole("button", { name: "Add another record" }).click();
    const section = page.locator(`[data-record-index="${index}"]`);
    await section.getByPlaceholder("subdomain").fill(record.name);
    await section.getByRole("button", { name: /^Record type/ }).click();
    await page
      .locator('[role="option"]')
      .filter({ hasText: recordTypeInfo(record.type).label })
      .click();
    await section.getByRole("textbox", { name: /^Value/ }).fill(record.value);
  }
  await page.getByRole("button", { name: "Create records" }).click();
  await expect(flash(page)).toContainText(`Records for ${ZONE} were successfully created.`);
  await expect(page.getByRole("tab", { name: `Records (${ALL_RECORDS})` })).toBeVisible();

  // "View status" follows the change: PENDING at first, INSYNC a few seconds later. The
  // records are already listed while it is pending.
  await flash(page).getByRole("button", { name: "View status" }).click();
  await expect(flash(page)).toContainText("Status: PENDING");
  await expect(flash(page)).toContainText(/Change C[A-Z0-9]{13}, submitted at/);
  await expect(flash(page)).toContainText("Status: INSYNC", { timeout: 30_000 });
  await expect(flash(page)).not.toContainText("Status: PENDING");

  // Search and filter.
  const filter = page.getByPlaceholder("Filter records by property or value");
  await filter.fill("www");
  await filter.press("Enter");
  await expect(page.getByText("5 matches").first()).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).first().click();
  await page.getByLabel("Filter by type").click();
  await page.getByRole("option", { name: "MX", exact: true }).click();
  await expect(page.getByText("1 match").first()).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).first().click();

  // Edit a record in the side panel.
  await page.getByTitle(`blog.${ZONE} is not selected`).click();
  await page.getByRole("button", { name: "Edit record" }).click();
  await page.getByLabel("TTL in seconds").fill("60");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(flash(page)).toContainText(`blog.${ZONE} was successfully updated.`);

  // The zone cannot be deleted while it has records of its own.
  await page.getByRole("button", { name: "Delete zone" }).click();
  await page.getByPlaceholder("delete").fill("delete");
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
  await expect(flash(page)).toContainText("contains non-required resource record sets");

  // Bulk delete everything except the zone's own NS and SOA.
  await page.reload();
  const rows = page.locator('table[aria-label="Records"] tbody tr');
  await expect(rows).toHaveCount(ALL_RECORDS);
  for (let index = 0; index < ALL_RECORDS; index += 1) {
    const row = rows.nth(index);
    // The record name is the row header (a <th>); the type is the first data cell after the checkbox.
    const name = (await row.locator("th").innerText()).trim();
    const type = (await row.locator("td").nth(1).innerText()).trim();
    const isDefault = name === ZONE && ["NS", "SOA"].includes(type);
    if (!isDefault) await row.locator("td").first().locator("label").click();
  }
  await page.getByRole("button", { name: "Delete records" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    `Delete ${RECORDS.length} selected records?`,
  );
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
  await expect(flash(page)).toContainText("The records were successfully deleted.");
  await expect(page.getByRole("tab", { name: "Records (2)" })).toBeVisible();

  // Sign out and back in: the zone is still there.
  await page.getByRole("button", { name: /Account menu/ }).click();
  await page.getByRole("menuitem", { name: /Sign out/ }).click();
  await expect(page).toHaveURL(/\/signin/);
  await signIn(page);
  await page.goto(zoneUrl);
  await expect(page.getByRole("tab", { name: "Records (2)" })).toBeVisible();

  // Delete the now-empty zone.
  await page.getByRole("button", { name: "Delete zone" }).click();
  await page.getByPlaceholder("delete").fill("delete");
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
  await expect(flash(page)).toContainText(`Hosted zone ${ZONE} was successfully deleted.`);
  await expect(page).toHaveURL(/\/route53\/v2\/hostedzones$/);
});

test("a session cookie survives a new browser context", async ({ browser }) => {
  const first = await browser.newContext();
  const page = await first.newPage();
  await page.goto("/signin");
  await signIn(page);
  await expect(page).toHaveURL(/\/route53\/v2\/hostedzones$/);
  const state = await first.storageState();
  await first.close();

  // A new context with only the saved cookie stands in for a browser restart.
  const second = await browser.newContext({ storageState: state });
  const restored = await second.newPage();
  await restored.goto("/route53/v2/hostedzones");
  await expect(restored.getByRole("heading", { name: /Hosted zones/ })).toBeVisible();
  await second.close();
});

test("placeholder sections show Coming soon inside the console frame", async ({ page }) => {
  await page.goto("/signin");
  await signIn(page);
  for (const [path, title] of [
    ["/route53/v2/home", "Dashboard"],
    ["/route53/v2/trafficflow/policies", "Traffic policies"],
    ["/route53/v2/healthchecks", "Health checks"],
    ["/route53/v2/resolver/inbound-endpoints", "Inbound endpoints"],
    ["/route53/v2/profiles", "Profiles"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: title, level: 1 })).toBeVisible();
    await expect(
      page.getByRole("main").getByRole("heading", { name: "Coming soon" }),
    ).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Breadcrumbs" })).toContainText(title);
  }
});

test("each visitor works in a private sandbox", async ({ browser }) => {
  const mine = await browser.newContext();
  const theirs = await browser.newContext();
  const myPage = await mine.newPage();
  const theirPage = await theirs.newPage();
  for (const page of [myPage, theirPage]) {
    await page.goto("/signin");
    await signIn(page);
  }
  const accountId = async (page: Page) =>
    (await (await page.request.get("/api/v1/auth/me")).json()).user.account_id as string;
  test.skip(
    (await accountId(myPage)) === (await accountId(theirPage)),
    "This deployment shares one account between visitors (R53_DEMO_SANDBOX is off).",
  );

  // Both start from the same sample zones.
  const sample = "example.org";
  const link = (page: Page, name: string) => page.getByRole("link", { name, exact: true });
  await expect(link(myPage, sample)).toBeVisible();
  await expect(link(theirPage, sample)).toBeVisible();

  // I delete a sample zone and create one of my own.
  await myPage.getByTitle(`${sample} is not selected`, { exact: true }).click();
  await myPage.getByRole("button", { name: "Delete", exact: true }).click();
  await myPage.getByPlaceholder("delete").fill("delete");
  await myPage.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
  await expect(flash(myPage)).toContainText(`Hosted zone ${sample} was successfully deleted.`);
  const created = await myPage.request.post("/api/v1/hostedzones", {
    data: { name: `private-${ZONE}` },
  });
  expect(created.status()).toBe(201);
  const zoneId = (await created.json()).id as string;
  await myPage.reload();
  await expect(link(myPage, `private-${ZONE}`)).toBeVisible();
  await expect(link(myPage, sample)).toHaveCount(0);

  // The other visitor sees neither change, in the list or by asking for the zone directly.
  await theirPage.reload();
  await expect(link(theirPage, sample)).toBeVisible();
  await expect(link(theirPage, `private-${ZONE}`)).toHaveCount(0);
  expect((await theirPage.request.get(`/api/v1/hostedzones/${zoneId}`)).status()).toBe(404);
  expect((await theirPage.request.delete(`/api/v1/hostedzones/${zoneId}`)).status()).toBe(404);

  // Signing out and in again in the same browser returns to my sandbox.
  await myPage.getByRole("button", { name: /^Account menu/ }).click();
  await myPage.getByRole("menuitem", { name: /^Sign out/ }).click();
  await expect(myPage).toHaveURL(/\/signin/);
  await signIn(myPage);
  await expect(link(myPage, `private-${ZONE}`)).toBeVisible();
  await expect(link(myPage, sample)).toHaveCount(0);

  await mine.close();
  await theirs.close();
});
