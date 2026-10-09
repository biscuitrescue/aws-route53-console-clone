import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const EMAIL = process.env.E2E_EMAIL ?? "demo@example.com";
const PASSWORD = process.env.E2E_PASSWORD ?? "Route53Demo!";
const API = "/api/v1";

const ZONE_FILE = `$TTL 300
ftp   IN A     192.0.2.50
files IN CNAME ftp
@     IN TXT   "imported by the end-to-end test"
`;

interface Zone {
  id: string;
  name: string;
}

/** Sign in through the API, so each test starts on the page it is about. */
async function signIn(page: Page) {
  const response = await page.request.post(`${API}/auth/login`, {
    data: { email: EMAIL, password: PASSWORD },
  });
  expect(response.ok()).toBeTruthy();
}

async function createZone(page: Page, label: string): Promise<Zone> {
  const name = `e2e-${label}-${Date.now().toString(36)}.example`;
  const response = await page.request.post(`${API}/hostedzones`, { data: { name } });
  expect(response.status()).toBe(201);
  return { id: (await response.json()).id, name };
}

/** Empty a zone and delete it, so runs against a shared deployment leave nothing behind. */
async function removeZone(page: Page, zone: Zone) {
  const records = await (
    await page.request.get(`${API}/hostedzones/${zone.id}/records?page_size=500`)
  ).json();
  const changes = records.items
    .filter(
      (record: { name: string; type: string }) =>
        !(record.name === `${zone.name}.` && ["NS", "SOA"].includes(record.type)),
    )
    .map((record: { name: string; type: string; set_identifier: string | null }) => ({
      action: "DELETE",
      record_set: {
        name: record.name,
        type: record.type,
        set_identifier: record.set_identifier,
      },
    }));
  if (changes.length > 0) {
    await page.request.post(`${API}/hostedzones/${zone.id}/records:batch`, { data: { changes } });
  }
  await page.request.delete(`${API}/hostedzones/${zone.id}`);
}

const flash = (page: Page) => page.getByRole("list", { name: "Notifications" });

/** Fail a test that logs a console error or gets a 5xx answer. */
function watchForProblems(page: Page): string[] {
  const problems: string[] = [];
  page.on("pageerror", (error) => problems.push(`page error: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !/status of 4\d\d/.test(message.text()))
      problems.push(`console: ${message.text().slice(0, 200)}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 500) problems.push(`${response.status()} ${response.url()}`);
  });
  return problems;
}

test("import a zone file with a preview, then export the zone", async ({ page }) => {
  const problems = watchForProblems(page);
  await signIn(page);
  const zone = await createZone(page, "transfer");

  await page.goto(`/route53/v2/hostedzones/${zone.id}`);
  await page.getByRole("link", { name: "Import zone file" }).click();
  const zoneFile = page.getByRole("textbox", { name: "Zone file" });

  // Errors are reported by line and block the import; nothing is saved.
  await zoneFile.fill("bad IN A 999.1.1.1\nnot a record line\n");
  await expect(page.getByText("The zone file has errors")).toBeVisible();
  await expect(page.getByText(/Line 1: .*not a valid IPv4 address/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Import", exact: true })).toBeDisabled();

  // A valid file is previewed before anything is created.
  await zoneFile.fill(ZONE_FILE);
  const preview = page.getByRole("table", { name: "Record preview" });
  await expect(preview.getByText("Will be created")).toHaveCount(3);
  await expect(preview).toContainText(`files.${zone.name}`);
  const before = await (await page.request.get(`${API}/hostedzones/${zone.id}`)).json();
  expect(before.record_count).toBe(2);

  await page.getByRole("button", { name: "Import", exact: true }).click();
  await expect(flash(page)).toContainText(`Records for ${zone.name} were successfully created.`);
  await expect(page.getByRole("tab", { name: "Records (5)" })).toBeVisible();

  // Importing the same file again fails as a whole: the records already exist.
  await page.getByRole("link", { name: "Import zone file" }).click();
  await page.getByRole("textbox", { name: "Zone file" }).fill(ZONE_FILE);
  await expect(page.getByRole("table", { name: "Record preview" })).toContainText(
    "but it already exists",
  );
  await expect(page.getByRole("button", { name: "Import", exact: true })).toBeDisabled();
  await page.getByRole("link", { name: "Cancel" }).click();

  // Export as a BIND zone file and as JSON.
  for (const [item, extension, expected] of [
    ["Zone file (BIND format)", "zone", `ftp.${zone.name}.\t300\tIN\tA\t192.0.2.50`],
    ["JSON", "json", `"Name":"files.${zone.name}."`],
  ]) {
    await page.getByRole("button", { name: "Export zone" }).click();
    const downloading = page.waitForEvent("download");
    await page.getByRole("menuitem", { name: item }).click();
    const download = await downloading;
    expect(download.suggestedFilename()).toBe(`${zone.name}.${extension}`);
    const stream = await download.createReadStream();
    let content = "";
    for await (const chunk of stream) content += chunk.toString();
    expect(content.replace(/\s+/g, " ")).toContain(expected.replace(/\s+/g, " "));
  }

  await removeZone(page, zone);
  expect(problems).toEqual([]);
});

test("bulk operations: edit the TTL of several records, then delete them", async ({ page }) => {
  const problems = watchForProblems(page);
  await signIn(page);
  const zone = await createZone(page, "bulk");
  const created = await page.request.post(`${API}/hostedzones/${zone.id}/records:batch`, {
    data: {
      changes: ["one", "two", "three"].map((name, index) => ({
        action: "CREATE",
        record_set: { name, type: "A", ttl: 300, values: [`192.0.2.${index + 1}`] },
      })),
    },
  });
  expect(created.ok()).toBeTruthy();

  await page.goto(`/route53/v2/hostedzones/${zone.id}`);
  for (const name of ["one", "two", "three"]) {
    await page.getByTitle(`${name}.${zone.name} is not selected`).click();
  }
  await expect(page.getByRole("heading", { name: "3 records selected" })).toBeVisible();

  await page.getByLabel("New TTL in seconds").fill("3600");
  await page.getByRole("button", { name: "Apply to 3 records" }).click();
  await expect(flash(page)).toContainText("3 records were successfully updated.");
  // The sticky header is a second table with the same label, so address the rows directly.
  const rows = page.locator('table[aria-label="Records"] tbody tr');
  await expect(rows.filter({ hasText: "3,600" })).toHaveCount(3);

  // The Delete key opens the same confirmation as the button.
  for (const name of ["one", "two"]) {
    await page.getByTitle(`${name}.${zone.name} is not selected`).click();
  }
  await page.getByRole("heading", { name: "2 records selected" }).click();
  await page.keyboard.press("Delete");
  await expect(page.getByRole("dialog")).toContainText("Delete 2 selected records?");
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
  await expect(flash(page)).toContainText("The records were successfully deleted.");
  await expect(page.getByRole("tab", { name: "Records (3)" })).toBeVisible();

  await removeZone(page, zone);
  expect(problems).toEqual([]);
});

test("keyboard shortcuts and the global search", async ({ page }) => {
  const problems = watchForProblems(page);
  await signIn(page);
  const zone = await createZone(page, "keys");
  await page.goto("/route53/v2/hostedzones");
  await expect(page.getByRole("link", { name: zone.name })).toBeVisible();

  // "?" lists the shortcuts of the page.
  await page.keyboard.press("?");
  const help = page.getByRole("dialog");
  await expect(help).toContainText("Keyboard shortcuts");
  await expect(help).toContainText("Create a hosted zone");
  await help.getByRole("button", { name: "Close", exact: true }).click();

  // "/" focuses the table filter; keys typed into a field are not shortcuts.
  await page.keyboard.press("/");
  const filter = page.getByPlaceholder("Filter records by property or value");
  await expect(filter).toBeFocused();
  await page.keyboard.type("c?");
  await expect(filter).toHaveValue("c?");
  await expect(page).toHaveURL(/\/hostedzones$/);
  await filter.fill("");
  await filter.blur();

  // Alt+S focuses the search field in the top bar, which finds hosted zones.
  await page.keyboard.press("Alt+s");
  const search = page.getByRole("combobox", { name: "Search", exact: true });
  await expect(search).toBeFocused();
  await search.fill(zone.name);
  await page.getByRole("dialog", { name: "Search results" }).getByText(zone.name).click();
  await expect(page).toHaveURL(new RegExp(`/hostedzones/${zone.id}$`));

  // "c" creates: a record on a zone page, a zone on the list.
  await expect(page.getByRole("tab", { name: "Records (2)" })).toBeVisible();
  await page.keyboard.press("c");
  await expect(page).toHaveURL(/\/records\/create$/);
  await page.goto("/route53/v2/hostedzones");
  await expect(page.getByRole("link", { name: zone.name })).toBeVisible();
  await page.keyboard.press("c");
  await expect(page).toHaveURL(/\/hostedzones\/create$/);

  await removeZone(page, zone);
  expect(problems).toEqual([]);
});

test("dark mode is chosen in the account menu and survives a reload", async ({ page }) => {
  // Light is the default even when the browser prefers dark.
  await page.emulateMedia({ colorScheme: "dark" });
  await signIn(page);
  await page.goto("/route53/v2/hostedzones");
  const body = page.locator("body");
  await expect(body).not.toHaveClass(/awsui-dark-mode/);

  await page.getByRole("button", { name: /Account menu/ }).click();
  await page.getByRole("button", { name: "Dark", exact: true }).click();
  await expect(body).toHaveClass(/awsui-dark-mode/);

  await page.reload();
  await expect(body).toHaveClass(/awsui-dark-mode/);
  await expect(page.getByRole("heading", { name: /Hosted zones/ })).toBeVisible();

  await page.getByRole("button", { name: /Account menu/ }).click();
  await page.getByRole("button", { name: "Light", exact: true }).click();
  await expect(body).not.toHaveClass(/awsui-dark-mode/);
});

test("header menus work and say what is only a placeholder", async ({ page }) => {
  await signIn(page);
  await page.goto("/route53/v2/hostedzones");

  await page.getByRole("button", { name: "Services" }).click();
  const services = page.getByRole("dialog", { name: "Services" });
  await services.getByRole("button", { name: "All services" }).click();
  await services.getByRole("button", { name: /Route 53/ }).click();
  await expect(page).toHaveURL(/\/route53\/v2\/home$/);

  await page.getByRole("button", { name: "Notifications (none available)" }).click();
  await expect(page.getByRole("dialog", { name: "Notifications" })).toContainText(
    "No notifications",
  );
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "CloudShell" }).first().click();
  await expect(flash(page)).toContainText("CloudShell is not available in this clone");

  await page.getByRole("button", { name: "Help & support" }).click();
  await page.getByRole("button", { name: "Keyboard shortcuts" }).click();
  await expect(page.getByRole("dialog")).toContainText("Show this list of keyboard shortcuts");
});

test("the wizard defines records for a routing policy and creates them together", async ({
  page,
}) => {
  const problems = watchForProblems(page);
  await signIn(page);
  const zone = await createZone(page, "wizard");
  await page.goto(`/route53/v2/hostedzones/${zone.id}/records/create`);

  await page.getByRole("button", { name: "Switch to wizard" }).click();
  await expect(page.getByRole("heading", { name: "Choose routing policy" })).toBeVisible();
  await page.getByText("Weighted", { exact: true }).click();
  await page.getByRole("button", { name: "Next" }).click();

  // Nothing defined yet: the wizard says so instead of sending an empty batch.
  await page.getByRole("button", { name: "Create records" }).click();
  await expect(page.getByText("Define at least one weighted record.").first()).toBeVisible();

  for (const [identifier, weight, address] of [
    ["blue", "70", "192.0.2.1"],
    ["green", "30", "192.0.2.2"],
  ]) {
    await page.getByRole("button", { name: "Define weighted record" }).first().click();
    const dialog = page.getByRole("dialog");
    await dialog.getByPlaceholder("subdomain").fill("app");
    await dialog.getByRole("textbox", { name: /^Value/ }).fill(address);
    await dialog.getByRole("spinbutton", { name: "Weight" }).fill(weight);
    await dialog.getByRole("textbox", { name: "Record ID" }).fill(identifier);
    await dialog.getByRole("button", { name: "Define weighted record" }).click();
    await expect(dialog).toBeHidden();
  }
  await expect(page.getByRole("table", { name: "Records to add" }).last()).toContainText(
    "192.0.2.2",
  );

  await page.getByRole("button", { name: "Create records" }).click();
  await expect(flash(page)).toContainText(`Records for ${zone.name} were successfully created.`);
  await expect(page.getByRole("tab", { name: "Records (4)" })).toBeVisible();
  const rows = page.locator('table[aria-label="Records"] tbody tr');
  await expect(rows.filter({ hasText: "Weighted" })).toHaveCount(2);

  await removeZone(page, zone);
  expect(problems).toEqual([]);
});

test("a private zone keeps its VPCs and tags, and both can be edited", async ({ page }) => {
  const problems = watchForProblems(page);
  await signIn(page);
  const name = `e2e-private-${Date.now().toString(36)}.internal`;
  await page.goto("/route53/v2/hostedzones/create");

  await page.getByPlaceholder("example.com").fill(name);
  await page.getByText("Private hosted zone", { exact: true }).click();
  // A private zone needs a complete VPC association before it can be created.
  await page.getByRole("button", { name: "Create hosted zone", exact: true }).click();
  await expect(page.getByText("Choose a Region.").first()).toBeVisible();
  await page.getByRole("button", { name: /^Region/ }).click();
  await page.getByRole("option", { name: /US East \(N\. Virginia\)/ }).click();
  await page.getByPlaceholder("Choose VPC").fill("vpc-0a1b2c3d");
  await page.getByRole("button", { name: "Add tag" }).click();
  await page.getByPlaceholder("Enter key").fill("env");
  await page.getByPlaceholder("Enter value").fill("test");
  await page.getByRole("button", { name: "Create hosted zone", exact: true }).click();
  await expect(flash(page)).toContainText(`${name} was successfully created.`);
  await expect(page.getByRole("tab", { name: "Hosted zone tags (1)" })).toBeVisible();
  const id = page.url().split("/").pop() as string;
  const zone: Zone = { id, name };

  await page.getByRole("link", { name: "Edit hosted zone" }).click();
  await page.getByPlaceholder("The hosted zone is used for...").fill("Edited by the test");
  await page.getByPlaceholder("Choose VPC").fill("vpc-11112222");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(flash(page)).toContainText(`Hosted zone ${name} was successfully updated.`);

  const saved = await (await page.request.get(`${API}/hostedzones/${id}`)).json();
  expect(saved.description).toBe("Edited by the test");
  expect(saved.vpcs).toEqual([{ vpc_id: "vpc-11112222", region: "us-east-1" }]);
  expect(saved.tags).toEqual([{ key: "env", value: "test" }]);

  await removeZone(page, zone);
  expect(problems).toEqual([]);
});

test("the records filter and its selects share one row as the page narrows", async ({ page }) => {
  await signIn(page);
  const zone = await createZone(page, "toolbar");
  const controls = () => [
    page.getByPlaceholder("Filter records by property or value"),
    page.getByRole("button", { name: "Filter by type" }),
    page.getByRole("button", { name: "Filter by routing policy" }),
    page.getByRole("button", { name: "Filter by alias" }),
  ];

  /** What is wrong with the filter row right now, or "none". */
  const rowProblem = async (): Promise<string> => {
    const boxes = [];
    for (const control of controls()) {
      const box = await control.boundingBox();
      if (!box) return "a control is not visible";
      boxes.push(box);
    }
    const centres = boxes.map((box) => box.y + box.height / 2);
    if (Math.max(...centres) - Math.min(...centres) >= 4) return "the controls are on two rows";
    // Left to right in the console's order, none overlapping the next.
    for (let index = 1; index < boxes.length; index++) {
      if (boxes[index].x < boxes[index - 1].x + boxes[index - 1].width)
        return "the controls overlap or are out of order";
    }
    const fits = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    return fits ? "none" : "the page scrolls sideways";
  };

  /** Open or close the side navigation, whatever state the page chose for this width. */
  const setNavigation = async (open: boolean) => {
    const isOpen = await page.getByRole("link", { name: "Health checks" }).isVisible();
    if (isOpen !== open) {
      await page
        .locator('button[aria-label*="navigation" i]')
        .filter({ visible: true })
        .first()
        .click();
      await expect(page.getByRole("link", { name: "Health checks" })).toBeVisible({
        visible: open,
      });
    }
  };

  // The states of the console's own captures. At 1920 px the navigation and the record
  // panel are both open, which is the narrowest the content gets on a desktop.
  const states = [
    { width: 1920, navigation: true },
    { width: 1300, navigation: false },
    { width: 950, navigation: false },
    { width: 800, navigation: true },
  ];
  for (const { width, navigation } of states) {
    await page.setViewportSize({ width, height: 1080 });
    await page.goto(`/route53/v2/hostedzones/${zone.id}`);
    await expect(page.getByRole("gridcell", { name: "SOA", exact: true })).toBeVisible();
    await setNavigation(navigation);

    // Polled, because the layout is still moving while the navigation opens or closes.
    await expect
      .poll(rowProblem, { message: `filter row at ${width} px`, timeout: 10_000 })
      .toBe("none");
  }

  // With room to spare the filter keeps the console's 648 px field.
  await page.setViewportSize({ width: 1920, height: 1080 });
  await setNavigation(false);
  await expect
    .poll(async () => Math.round((await controls()[0].boundingBox())!.width))
    .toBeGreaterThan(600);

  await removeZone(page, zone);
});
