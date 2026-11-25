import { readFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

// PRD 037: a two-channel Teams capture streams while recording, then each channel is processed on its own.
// The browser's fake devices stand in for hardware: the screen picker is answered automatically and the
// microphone plays APP_E2E_CAPTURE_SPEECH when given. Real system audio from Teams is verified by hand.
const tr = JSON.parse(await readFile(new URL("../../app/frontend/src/locales/tr.json", import.meta.url), "utf8"));
const speech = process.env.APP_E2E_CAPTURE_SPEECH;
const seconds = Number(process.env.APP_E2E_CAPTURE_SECONDS || 20);
const launchArgs = [
  "--use-fake-ui-for-media-stream",
  "--use-fake-device-for-media-stream",
  "--auto-select-desktop-capture-source=Entire screen",
  ...(speech ? [`--use-file-for-fake-audio-capture=${speech}`] : []),
];

await withBrowser("Two-channel Teams capture streams during recording and processes each channel", async ({ page, assert }) => {
  const username = process.env.APP_E2E_ROSTER_USER;
  const password = process.env.APP_E2E_ROSTER_PASS;
  assert.ok(username && password, "An ordinary meeting account is required");
  const failures = [];
  const parts = [];
  const ids = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (request.method() === "PUT" && path.includes("/capture-frames/")) parts.push(Number(path.split("/").pop()));
  });
  page.on("response", async (response) => {
    if (response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/meetings/captures") && response.status() === 201) {
      ids.push((await response.json()).public_id);
    }
  });
  async function request(path, method = "GET") {
    return page.evaluate(async ({ path, method }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { method, headers: {
        Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id,
      } });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    }, { path, method });
  }

  await page.goto(baseUrl + "/login");
  await page.getByLabel(tr["login.username"], { exact: true }).fill(username);
  await page.getByLabel(tr["login.password"], { exact: true }).fill(password);
  await page.getByRole("button", { name: tr["login.submit"], exact: true }).click();
  await page.waitForURL(baseUrl + "/");
  try {
    await page.goto(baseUrl + "/meetings?new=teams");
    await page.getByRole("button", { name: tr["capture.source"], exact: true, pressed: true }).waitFor();
    await page.getByLabel(tr["meeting.titleLabel"], { exact: true }).fill("E2E Teams");
    const start = page.getByRole("button", { name: tr["capture.start"], exact: true });
    assert.equal(await start.isDisabled(), true, "Recording waits until the participants were informed");
    await page.getByRole("checkbox", { name: tr["capture.consent"], exact: true }).check();
    await start.click();
    const finish = page.getByRole("button", { name: tr["capture.finish"], exact: true });
    await finish.waitFor({ timeout: 30000 });
    await page.getByRole("status").filter({ hasText: tr["capture.phase.recording"] }).waitFor();
    await page.waitForFunction((target) => Number(document.querySelector("[data-capture-seconds]")?.getAttribute("data-capture-seconds")) >= target,
      seconds, { timeout: (seconds + 30) * 1000 });
    assert.ok(parts.length >= Math.floor(seconds / 2) - 1, `Parts stream during the recording (${parts.length})`);
    assert.deepEqual(parts, [...parts].sort((a, b) => a - b), "Parts are sent in order");
    await page.getByRole("checkbox", { name: tr["capture.microphoneMute"], exact: true }).waitFor();
    await finish.click();
    await page.waitForURL(/\/meetings\/[0-9a-f-]{36}/, { timeout: 120000 });
    assert.equal(ids.length, 1, "One meeting was created");
    const created = await request(`/meetings/${ids[0]}`);
    assert.equal(created.body.capture_mode, "two_channel");
    assert.notEqual(created.body.status, "uploading", "Finishing queues the meeting");
    assert.ok(created.body.duration_seconds >= seconds && created.body.duration_seconds < seconds + 10, "The whole recording arrived");
    await page.waitForFunction(() => document.querySelector("[data-meeting-status]")?.getAttribute("data-meeting-status") === "succeeded",
      undefined, { timeout: 30 * 60 * 1000 });
    const speakers = await request(`/meetings/${ids[0]}/speakers?offset=0&limit=20`);
    assert.ok(speakers.body.items.every((speaker) => ["microphone", "system"].includes(speaker.channel)), "Every speaker carries its channel");
    if (speech) {
      assert.ok(speakers.body.items.some((speaker) => speaker.channel === "microphone"), "The microphone speech became a speaker");
      await page.getByText(tr["meeting.channel.microphone"], { exact: true }).first().waitFor();
    }
    assert.deepEqual(failures, []);
  } finally {
    for (const id of ids) {
      await request(`/meetings/${id}/cancel`, "POST");
      const removed = await request(`/meetings/${id}`, "DELETE");
      assert.ok([204, 404, 409].includes(removed.status), `cleanup returned ${removed.status}`);
    }
  }
}, { requireCredentials: false, launchArgs, headless: process.env.APP_E2E_HEADED !== "1" });
