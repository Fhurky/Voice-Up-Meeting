import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const tr = JSON.parse(await readFile(new URL("../../app/frontend/src/locales/tr.json", import.meta.url), "utf8"));

await withBrowser("MP4 meeting upload sends only the extracted audio", async ({ page, assert }) => {
  const username = process.env.APP_E2E_ROSTER_USER;
  const password = process.env.APP_E2E_ROSTER_PASS;
  const fixture = process.env.APP_E2E_MP4_FIXTURE;
  assert.ok(username && password, "An ordinary meeting account is required");
  assert.ok(fixture, "APP_E2E_MP4_FIXTURE must name an MP4 with an audio track");
  const video = await readFile(fixture);
  const videoHash = createHash("sha256").update(video).digest("hex");
  const failures = [];
  const created = [];
  const uploads = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST" && path.endsWith("/meetings")) created.push(JSON.parse(request.postData()));
    if (request.method() === "PUT" && path.includes("/upload-parts/")) uploads.push(request.postDataBuffer());
  });
  const ids = [];
  page.on("response", async (response) => {
    if (response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/meetings") && response.status() === 201) {
      ids.push((await response.json()).public_id);
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
  await page.getByLabel(tr["login.username"], { exact: true }).fill(username);
  await page.getByLabel(tr["login.password"], { exact: true }).fill(password);
  await page.getByRole("button", { name: tr["login.submit"], exact: true }).click();
  await page.waitForURL(baseUrl + "/");
  try {
    await page.goto(baseUrl + "/meetings?new=file");
    await page.getByLabel(tr["meeting.titleLabel"], { exact: true }).fill("E2E MP4");
    await page.getByLabel(tr["meeting.file"], { exact: true }).setInputFiles(fixture);
    await page.getByRole("button", { name: tr["meeting.start"], exact: true }).click();
    await page.waitForURL(/\/meetings\/[0-9a-f-]{36}/, { timeout: 120000 });
    await page.locator("[data-meeting-status]").first().waitFor();
    assert.equal(created.length, 1);
    assert.equal(created[0].format, "WAV", "The server receives a WAV");
    await page.waitForFunction(() => document.querySelector("[data-meeting-status]")?.getAttribute("data-meeting-status") !== "uploading", undefined, { timeout: 120000 });
    assert.ok(uploads.length > 0, "Audio parts were uploaded");
    const bytes = Buffer.concat(uploads);
    assert.equal(bytes.length, created[0].size_bytes);
    assert.equal(bytes.subarray(0, 4).toString("latin1"), "RIFF");
    assert.equal(bytes.readUInt32LE(24), 16000);
    assert.equal(bytes.readUInt16LE(22), 1, "The audio is mono");
    const seconds = Number(process.env.APP_E2E_MP4_SECONDS);
    if (seconds) assert.ok(Math.abs((bytes.length - 44) / 32000 - seconds) < 0.25, "The audio keeps the video's duration");
    let peak = 0;
    for (let offset = 44; offset + 1 < bytes.length; offset += 2) peak = Math.max(peak, Math.abs(bytes.readInt16LE(offset)));
    assert.ok(peak > 1000, "The extracted audio is not silent");
    assert.notEqual(createHash("sha256").update(bytes).digest("hex"), videoHash);
    assert.ok(!bytes.includes(video.subarray(0, 64)), "No video bytes reach the server");
    assert.deepEqual(failures, []);
  } finally {
    for (const id of ids) {
      await request(`/meetings/${id}/cancel`, "POST");
      const removed = await request(`/meetings/${id}`, "DELETE");
      assert.ok([204, 404, 409].includes(removed.status), `cleanup returned ${removed.status}`);
    }
  }
}, { requireCredentials: false });
