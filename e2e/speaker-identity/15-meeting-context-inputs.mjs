import { randomUUID } from "node:crypto";
import { mkdir, readFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));

function silentWav(seconds = 2, rate = 16000) {
  const data = Buffer.alloc(seconds * rate * 2);
  const header = Buffer.alloc(44);
  header.write("RIFF", 0); header.writeUInt32LE(36 + data.length, 4); header.write("WAVEfmt ", 8);
  header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20); header.writeUInt16LE(1, 22);
  header.writeUInt32LE(rate, 24); header.writeUInt32LE(rate * 2, 28); header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34); header.write("data", 36); header.writeUInt32LE(data.length, 40);
  return Buffer.concat([header, data]);
}

await withBrowser("meeting subject and expected questions", async ({ page, assert }) => {
  const username = process.env.APP_E2E_ROSTER_USER;
  const password = process.env.APP_E2E_ROSTER_PASS;
  assert.ok(username && password, "An ordinary meeting account is required");
  const failures = [];
  const created = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") failures.push(message.text()); });
  page.on("response", async (response) => {
    const path = new URL(response.url()).pathname;
    if (response.request().method() === "POST" && path.endsWith("/meetings") && response.status() === 201) {
      created.push((await response.json()).public_id);
    }
  });
  async function request(path, method = "GET") {
    return page.evaluate(async ({ path, method }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { method, headers: {
        Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id,
      } });
      return { status: response.status };
    }, { path, method });
  }

  await page.goto(baseUrl + "/login");
  await page.getByLabel(catalogues.tr["login.username"], { exact: true }).fill(username);
  await page.getByLabel(catalogues.tr["login.password"], { exact: true }).fill(password);
  const loginResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
  await page.getByRole("button", { name: catalogues.tr["login.submit"], exact: true }).click();
  const identity = (await (await loginResponse).json()).user;
  assert.equal(identity.is_super_admin, false, "Meeting details must work for an ordinary role");
  await page.waitForURL(baseUrl + "/");

  try {
    for (const [locale, width] of [["tr", 1440], ["en", 390]]) {
      const text = catalogues[locale];
      await page.setViewportSize({ width, height: 900 });
      await page.goto(baseUrl + "/meetings?new=file");
      if (locale === "en") await page.getByRole("button", { name: catalogues.tr["common.otherLanguage"], exact: true }).click();
      await page.getByText(text["meeting.context.title"], { exact: true }).click();
      const subject = `E2E ${locale} ${randomUUID().slice(0, 8)}`;
      await page.getByLabel(text["meeting.context.subject"], { exact: true }).fill(subject);
      const list = page.getByRole("group", { name: text["meeting.context.questions"], exact: true });
      const add = list.getByRole("button", { name: text["meeting.context.addQuestion"], exact: true });
      await add.click();
      const first = list.getByRole("textbox", { name: text["meeting.context.question"].replace("{number}", "1"), exact: true });
      assert.equal(await first.evaluate((element) => element === document.activeElement), true, "A new question row takes focus");
      await first.fill("Bütçe onaylandı mı?");
      await add.click();
      const second = list.getByRole("textbox", { name: text["meeting.context.question"].replace("{number}", "2"), exact: true });
      await second.fill("bütçe  onaylandı mı?");
      await page.getByLabel(text["meeting.titleLabel"], { exact: true }).fill(subject);
      await page.getByLabel(text["meeting.file"], { exact: true }).setInputFiles({ name: "details.wav", mimeType: "audio/wav", buffer: silentWav() });
      await page.getByRole("button", { name: text["meeting.start"], exact: true }).click();
      await page.getByRole("alert").filter({ hasText: text["meeting.error.duplicateQuestion"] }).waitFor();
      assert.equal(created.length, locale === "tr" ? 0 : 1, "A repeated question creates nothing");
      await second.fill("Kim sorumlu?");
      const widths = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth }));
      assert.ok(widths.content <= widths.viewport + 1, `details overflow at ${width}px`);
      await mkdir("test-results", { recursive: true });
      await page.screenshot({ path: `test-results/meeting-details-${locale}-${width}.png`, fullPage: true });
      await page.getByRole("button", { name: text["meeting.start"], exact: true }).click();
      await page.waitForURL(/\/meetings\/[0-9a-f-]{36}/);
      await page.getByRole("heading", { name: text["meeting.context.title"], exact: true }).waitFor();
      await page.getByText(subject, { exact: true }).last().waitFor();
      const items = page.locator(".meeting-context li");
      assert.deepEqual(await items.allTextContents(), ["Bütçe onaylandı mı?", "Kim sorumlu?"]);
    }
    assert.deepEqual(failures, []);
  } finally {
    for (const id of created) {
      await request(`/meetings/${id}/cancel`, "POST");
      const removed = await request(`/meetings/${id}`, "DELETE");
      assert.ok([204, 404, 409].includes(removed.status), `cleanup of ${id} returned ${removed.status}`);
    }
  }
}, { requireCredentials: false });
