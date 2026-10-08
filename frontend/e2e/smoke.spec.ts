import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { recordTypeInfo } from "../lib/record-types";
import type { RecordType } from "../lib/api/types";

const EMAIL = process.env.E2E_EMAIL ?? "demo@example.com";
const PASSWORD = process.env.E2E_PASSWORD ?? "Route53Demo!";

/** A zone name no other run uses, so the test can run against a shared demo. */
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
];

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
  await expect(page.getByRole("tab", { name: "Records (11)" })).toBeVisible();

  // Search and filter.
  const filter = page.getByPlaceholder("Filter records by property or value");
  await filter.fill("www");
  await filter.press("Enter");
  await expect(page.getByText("4 matches").first()).toBeVisible();
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
  await expect(rows).toHaveCount(11);
  for (let index = 0; index < 11; index += 1) {
    const row = rows.nth(index);
    // The record name is the row header (a <th>); the type is the first data cell after the checkbox.
    const name = (await row.locator("th").innerText()).trim();
    const type = (await row.locator("td").nth(1).innerText()).trim();
    const isDefault = name === ZONE && ["NS", "SOA"].includes(type);
    if (!isDefault) await row.locator("td").first().locator("label").click();
  }
  await page.getByRole("button", { name: "Delete record" }).click();
  await expect(page.getByRole("dialog")).toContainText("Delete 9 selected records?");
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
