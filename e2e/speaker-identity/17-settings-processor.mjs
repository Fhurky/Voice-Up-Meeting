import { readFile } from "node:fs/promises";
import { baseUrl, password, username, withBrowser } from "../shared/harness.mjs";

const tr = JSON.parse(await readFile(new URL("../../app/frontend/src/locales/tr.json", import.meta.url), "utf8"));
const SWITCH_TIMEOUT = 300_000;

async function login(page, user, secret) {
  await page.goto(baseUrl + "/login");
  await page.getByLabel(tr["login.username"], { exact: true }).fill(user);
  await page.getByLabel(tr["login.password"], { exact: true }).fill(secret);
  const response = page.waitForResponse((item) => new URL(item.url()).pathname.endsWith("/auth/login"));
  await page.getByRole("button", { name: tr["login.submit"], exact: true }).click();
  const identity = (await (await response).json()).user;
  await page.waitForURL(baseUrl + "/");
  return identity;
}

async function changeTo(page, assert, device) {
  const label = device.toUpperCase();
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.locator(`[data-processor-device="${device}"]`).waitFor({ timeout: SWITCH_TIMEOUT });
  assert.equal(await page.getByRole("button", { name: label, exact: true }).getAttribute("aria-pressed"), "true");
  assert.equal(await page.getByRole("alert").count(), 0, "A successful change shows no error");
}

await withBrowser("administrator changes the meeting processor from settings", async ({ page, assert }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));
  const identity = await login(page, username, password);
  assert.equal(identity.is_super_admin, true, "This scenario needs the application administrator");
  await page.getByRole("link", { name: tr["nav.settings"], exact: true }).click();
  await page.waitForURL(baseUrl + "/settings");
  await page.getByRole("heading", { name: tr["settings.processor.title"], exact: true }).waitFor();
  // Both processors are exercised from whichever one is running, and that one is restored.
  const panel = page.locator("[data-processor-device]");
  await panel.waitFor();
  const original = await panel.getAttribute("data-processor-device");
  assert.ok(original === "gpu" || original === "cpu", "The scenario needs a settled processor");
  const other = original === "gpu" ? "cpu" : "gpu";
  try {
    await changeTo(page, assert, other);
    await page.getByText(tr[`settings.processor.${other}Hint`], { exact: true }).waitFor();
    await page.goto(baseUrl + "/settings");
    await page.locator(`[data-processor-device="${other}"]`).waitFor();
  } finally {
    await page.locator(`[data-processor-device="${other}"], [data-processor-device="${original}"]`).waitFor({ timeout: SWITCH_TIMEOUT });
    if (await panel.getAttribute("data-processor-device") !== original) await changeTo(page, assert, original);
  }
  assert.deepEqual(failures, []);
});

await withBrowser("an ordinary user neither sees nor reaches the processor setting", async ({ page, assert }) => {
  const user = process.env.APP_E2E_ROSTER_USER;
  const secret = process.env.APP_E2E_ROSTER_PASS;
  assert.ok(user && secret, "An ordinary meeting account is required");
  const identity = await login(page, user, secret);
  assert.equal(identity.is_super_admin, false, "The gate must be proven with an ordinary role");
  assert.equal(await page.getByRole("link", { name: tr["nav.settings"], exact: true }).count(), 0);
  await page.goto(baseUrl + "/settings");
  await page.getByRole("heading", { name: tr["common.forbidden"], exact: true }).waitFor();
  const statuses = await page.evaluate(async () => {
    const account = JSON.parse(localStorage.getItem("voiceup.user") || "null");
    const headers = {
      Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"),
      "x-tenant-id": account.tenant_id,
      "Content-Type": "application/json",
    };
    const read = await fetch("/api/voiceup/v1/meetings/processor", { headers });
    const change = await fetch("/api/voiceup/v1/meetings/processor", {
      method: "PUT", headers, body: JSON.stringify({ device: "cpu" }),
    });
    return [read.status, change.status];
  });
  assert.deepEqual(statuses, [403, 403]);
}, { requireCredentials: false });
