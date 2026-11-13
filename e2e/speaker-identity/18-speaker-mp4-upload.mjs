import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { basename } from "node:path";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const tr = JSON.parse(await readFile(new URL("../../app/frontend/src/locales/tr.json", import.meta.url), "utf8"));

await withBrowser("speaker profile and identification from MP4 videos", async ({ page, assert }) => {
  const username = process.env.APP_E2E_ENROLL_USER;
  const password = process.env.APP_E2E_ENROLL_PASS;
  const enrollVideo = process.env.APP_E2E_SPEAKER_MP4;
  const queryVideo = process.env.APP_E2E_SPEAKER_MP4_QUERY;
  assert.ok(username && password, "An ordinary account with profile and analysis rights is required");
  assert.ok(enrollVideo && queryVideo, "Two MP4 videos of one speaker talking alone are required");
  const profiles = [];
  const recordings = [];
  const uploads = [];
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname.endsWith("/recordings")) uploads.push(request.postDataBuffer());
  });
  page.on("response", async (response) => {
    if (response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/recordings") && response.status() === 201) {
      recordings.push((await response.json()).public_id);
    }
  });
  async function publicRequest(path, method = "GET") {
    return page.evaluate(async ({ path, method }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, {
        method, headers: { Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id },
      });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    }, { path, method });
  }
  async function finishedJob() {
    await page.waitForURL(/\/speaker-jobs\/[a-f0-9-]+$/);
    return (await publicRequest("/speaker-jobs/" + new URL(page.url()).pathname.split("/").at(-1))).body;
  }
  const navigation = () => page.getByRole("navigation", { name: tr["nav.main"] });

  await page.goto(baseUrl + "/login");
  await page.getByLabel(tr["login.username"], { exact: true }).fill(username);
  await page.getByLabel(tr["login.password"], { exact: true }).fill(password);
  const login = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
  await page.getByRole("button", { name: tr["login.submit"], exact: true }).click();
  assert.equal((await (await login).json()).user.is_super_admin, false, "MP4 upload must work for an ordinary role");
  await page.waitForURL(baseUrl + "/");

  let failure = null;
  try {
    const name = `E2E MP4 ${randomUUID().slice(0, 8)}`;
    await navigation().getByRole("link", { name: tr["nav.profiles"], exact: true }).click();
    await page.getByRole("button", { name: tr["speaker.profiles.create"], exact: true }).click();
    // Capable browsers open profile creation on the microphone; this scenario uses the file source.
    const fileSource = page.getByRole("button", { name: tr["microphone.fileSource"], exact: true });
    if (await fileSource.count()) await fileSource.click();
    await page.getByLabel(tr["speaker.profiles.name"]).fill(name);
    await page.getByLabel(tr["speaker.audio.file"]).setInputFiles(enrollVideo);
    await page.getByRole("button", { name: tr["speaker.submit.enroll"], exact: true }).click();
    await page.getByRole("heading", { name: tr["speaker.decision.enrolled"], exact: true }).waitFor({ timeout: 120_000 });
    const enrolled = await finishedJob();
    if (enrolled.result?.profile_public_id) profiles.push(enrolled.result.profile_public_id);
    assert.equal(enrolled.result.decision, "enrolled");

    await navigation().getByRole("link", { name: tr["nav.analysis"], exact: true }).click();
    await page.getByLabel(tr["speaker.audio.file"]).setInputFiles(queryVideo);
    await page.getByRole("button", { name: tr["speaker.submit.identify"], exact: true }).click();
    await page.getByRole("heading", { name: tr["speaker.decision.recognized"], exact: true }).waitFor({ timeout: 120_000 });
    const identified = await finishedJob();
    assert.equal(identified.result.profile_public_id, enrolled.result.profile_public_id, "The other video of the same person is recognized");

    // Only a WAV of the extracted audio reaches the server; the video container never does.
    assert.equal(uploads.length, 2);
    for (const [index, video] of [enrollVideo, queryVideo].entries()) {
      const body = uploads[index];
      assert.ok(body.includes(`filename="${basename(video).replace(/\.mp4$/i, ".wav")}"`), "The upload is named as a WAV");
      assert.ok(body.includes("RIFF") && body.includes("WAVE"), "The upload is a WAV file");
      assert.ok(!body.includes("ftyp") && !body.includes("moov"), "No MP4 bytes are uploaded");
    }
    assert.deepEqual(failures, []);
  } catch (error) { failure = error; }
  // Cleanup runs either way and never hides the failure that stopped the scenario.
  const cleanup = [];
  for (const id of profiles) cleanup.push((await publicRequest("/speaker-profiles/" + id, "DELETE")).status);
  for (const id of recordings) cleanup.push((await publicRequest("/recordings/" + id, "DELETE")).status);
  if (failure) throw failure;
  assert.ok(cleanup.every((status) => [204, 404].includes(status)), `Test data cleanup returned ${cleanup.join(", ")}`);
}, { requireCredentials: false });
