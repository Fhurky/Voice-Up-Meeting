import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));
const liveMicrophone = process.env.APP_E2E_MICROPHONE_LIVE === "1";
const captureSeconds = Number(process.env.APP_E2E_MICROPHONE_SECONDS || "35");
const spokenLanguage = process.env.APP_E2E_MICROPHONE_LANGUAGE || "tr";

await withBrowser("microphone source controls and optional physical capture", async ({ page, assert }) => {
  const writer = process.env.APP_E2E_MEETING_USER;
  const secret = process.env.APP_E2E_MEETING_PASS;
  const reader = process.env.APP_E2E_MEETING_READER_USER;
  const readerSecret = process.env.APP_E2E_MEETING_READER_PASS;
  assert.ok(writer && secret && reader && readerSecret, "Ordinary meeting writer and reader credentials are required");
  assert.ok(Number.isSafeInteger(captureSeconds) && captureSeconds >= 25 && captureSeconds <= 300);
  assert.ok(["tr", "en", "auto"].includes(spokenLanguage));
  const prefix = `E2E microphone ${randomUUID()}`;
  const meetings = new Set();
  const profiles = new Set();
  const pendingResponses = [];
  const errors = [];
  const observations = [];
  const mutations = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/") && request.method() !== "GET" && !path.endsWith("/auth/login")) {
      mutations.push({ method: request.method(), path });
    }
  });
  page.on("response", (response) => {
    if (new URL(response.url()).pathname !== "/api/voiceup/v1/meetings" || response.request().method() !== "POST" || response.status() !== 201) return;
    const body = response.request().postDataJSON();
    if (typeof body?.title !== "string" || !body.title.startsWith(prefix)) return;
    pendingResponses.push(response.json().then((created) => meetings.add(created.public_id)));
  });

  async function setLocale(locale) {
    const switcher = page.getByRole("button", { name: catalogues[locale === "tr" ? "en" : "tr"]["common.otherLanguage"], exact: true });
    if (await switcher.count()) await switcher.click();
  }
  async function login(user, password) {
    await page.goto(baseUrl + "/login");
    await setLocale("tr");
    await page.getByLabel(catalogues.tr["login.username"], { exact: true }).fill(user);
    await page.getByLabel(catalogues.tr["login.password"], { exact: true }).fill(password);
    const responsePromise = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
    await page.getByRole("button", { name: catalogues.tr["login.submit"], exact: true }).click();
    const response = await responsePromise;
    assert.equal(response.status(), 200);
    const identity = (await response.json()).user;
    assert.equal(identity.is_super_admin, false);
    assert.ok(!identity.permissions.includes("*:*"));
    await page.waitForURL(baseUrl + "/");
    return identity;
  }
  async function logout() {
    for (const locale of ["tr", "en"]) {
      const button = page.getByRole("button", { name: catalogues[locale]["common.signOut"], exact: true });
      if (await button.count()) { await button.click(); return; }
    }
  }
  async function request(path, method = "GET") {
    return page.evaluate(async ({ path, method }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { method, headers: {
        Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id,
      } });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    }, { path, method });
  }
  async function captureAtLeast(seconds) {
    await page.waitForFunction((minimum) => {
      const element = document.querySelector('[data-recording-state="recording"]');
      return element && Number(element.getAttribute("data-recording-seconds")) >= minimum;
    }, seconds, { timeout: (seconds + 30) * 1000 });
  }
  async function inspectControls(locale) {
    const text = catalogues[locale];
    await page.goto(baseUrl + "/meetings");
    await setLocale(locale);
    const group = page.getByRole("group", { name: text["microphone.source"], exact: true });
    await group.getByRole("button", { name: text["microphone.microphoneSource"], exact: true }).click();
    assert.equal(await group.getByRole("button", { name: text["microphone.microphoneSource"], exact: true }).getAttribute("aria-pressed"), "true");
    assert.equal(await page.getByLabel(text["meeting.file"], { exact: true }).count(), 0);
    const title = `${prefix} ${locale}`;
    await page.getByLabel(text["meeting.titleLabel"], { exact: true }).fill(title);
    await page.getByLabel(text["meeting.language"], { exact: true }).selectOption(spokenLanguage);
    await page.getByText(text["meeting.advancedOptions"], { exact: true }).click();
    await page.getByLabel(text["meeting.participants"], { exact: true }).fill("1");
    await page.getByLabel(text["meeting.expectedSpeakers"], { exact: true }).fill("1");
    await page.getByRole("checkbox", { name: text["meeting.remember"], exact: true }).check();
    await page.getByLabel(text["microphone.device"], { exact: true }).waitFor();
    const tree = await page.locator("body").ariaSnapshot();
    for (const key of ["microphone.device", "microphone.duration", "microphone.level", "microphone.start"]) assert.ok(tree.includes(text[key]));
    const supported = !(await page.getByRole("button", { name: text["microphone.start"], exact: true }).isDisabled());
    if (!supported) assert.ok(await page.getByRole("alert").count(), "Unavailable capture must explain its prerequisite");
    await group.getByRole("button", { name: text["microphone.fileSource"], exact: true }).click();
    await page.getByLabel(text["meeting.file"], { exact: true }).waitFor();
    assert.equal(await page.getByLabel(text["meeting.titleLabel"], { exact: true }).inputValue(), title);
    await group.getByRole("button", { name: text["microphone.microphoneSource"], exact: true }).click();
    observations.push({ locale, source_controls: true, shared_options_preserved: true, capture_supported: supported });
    return supported;
  }
  async function capture(locale) {
    const text = catalogues[locale];
    const start = page.getByRole("button", { name: text["microphone.start"], exact: true });
    const beforeCancel = meetings.size;
    await start.click();
    await captureAtLeast(1);
    assert.equal(await page.getByLabel(text["microphone.device"], { exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole("button", { name: text["microphone.fileSource"], exact: true }).isDisabled(), true);
    await page.getByRole("button", { name: text["microphone.cancel"], exact: true }).click();
    await page.locator('[data-recording-state="idle"]').waitFor();
    await Promise.all(pendingResponses);
    assert.equal(meetings.size, beforeCancel, "Cancelling capture must not create a meeting");
    const before = meetings.size;
    console.log(`Physical microphone ${locale}: supply clean speech until the UI reaches ${captureSeconds} seconds.`);
    await start.click();
    await captureAtLeast(captureSeconds);
    assert.equal(meetings.size, before, "Recording alone must not create a meeting");
    const observedSeconds = Number(await page.locator("[data-recording-seconds]").getAttribute("data-recording-seconds"));
    await page.getByRole("button", { name: text["microphone.stop"], exact: true }).click();
    await page.waitForURL(/\/meetings\/[a-f0-9-]+$/, { timeout: 120_000 });
    const id = new URL(page.url()).pathname.split("/").at(-1);
    meetings.add(id);
    await page.locator('[data-meeting-status="succeeded"], [data-meeting-status="failed"]').waitFor({ timeout: 1_200_000 });
    const result = await request(`/meetings/${id}`);
    assert.equal(result.status, 200);
    assert.equal(result.body.status, "succeeded", "A real completed recording must pass the real decoder and model");
    assert.equal(result.body.format, "WAV");
    assert.equal(result.body.uploaded_bytes, result.body.size_bytes);
    assert.match(result.body.sha256, /^[a-f0-9]{64}$/);
    assert.ok(result.body.duration_seconds >= observedSeconds - 0.1 && result.body.duration_seconds <= observedSeconds + 5);
    const speakers = await request(`/meetings/${id}/speakers?offset=0&limit=100`);
    const transcript = await request(`/meetings/${id}/transcript?offset=0&limit=100`);
    assert.equal(speakers.status, 200); assert.equal(transcript.status, 200);
    assert.ok(speakers.body.total > 0, "Silence does not prove speaker recognition");
    assert.equal(transcript.body.provisional, false);
    assert.ok(transcript.body.items.some((turn) => turn.text.trim()), "Silence or an empty transcript is not speech acceptance");
    assert.ok(speakers.body.items.every((speaker) => ["profile_pending", "recognized", "enrolled", "ambiguous"].includes(speaker.decision)));
    for (const speaker of speakers.body.items) if (speaker.decision === "enrolled" && speaker.profile_public_id) profiles.add(speaker.profile_public_id);
    await page.locator("[data-transcript-id]").first().waitFor();
    await page.locator("[data-speaker-id]").first().waitFor();
    observations.push({ locale, physical_capture: true, cancel: true, completed_source: true,
      source_seconds: result.body.duration_seconds, nonempty_transcript: true, observed_speakers: speakers.body.total,
      decisions: speakers.body.items.map((speaker) => speaker.decision) });
  }

  try {
    const identity = await login(writer, secret);
    assert.ok(identity.permissions.includes("meeting_analysis:run") && identity.permissions.includes("speaker_profiles:write"));
    if (liveMicrophone) {
      assert.equal((await request("/speaker-profiles?offset=0&limit=20")).body.total, 0, "Physical capture uses an explicitly empty isolated fixture tenant");
      // This grants browser permission for actual hardware; no fake input, recorder, model, or session is installed.
      // It does not count as observing the browser's human permission prompt.
      await page.context().grantPermissions(["microphone"], { origin: new URL(baseUrl).origin });
    }
    for (const locale of ["tr", "en"]) {
      const supported = await inspectControls(locale);
      if (liveMicrophone) {
        assert.equal(supported, true, "Live physical capture requires the browser's real microphone and OPFS APIs");
        await capture(locale);
      }
    }
    if (!liveMicrophone) assert.deepEqual(mutations, [], "Control inspection must create no meetings or profiles");
    await logout();
    const readIdentity = await login(reader, readerSecret);
    assert.ok(!readIdentity.permissions.includes("meeting_analysis:run"));
    for (const locale of ["tr", "en"]) {
      await page.goto(baseUrl + "/meetings");
      await setLocale(locale);
      await page.getByRole("heading", { name: catalogues[locale]["meeting.listTitle"], level: 1, exact: true }).waitFor();
      assert.equal(await page.getByRole("group", { name: catalogues[locale]["microphone.source"], exact: true }).count(), 0);
      assert.equal(await page.getByRole("button", { name: catalogues[locale]["microphone.start"], exact: true }).count(), 0);
      observations.push({ locale, ordinary_reader: true, capture_controls_absent: true });
    }
    assert.deepEqual(errors, []);
    await mkdir("test-results", { recursive: true });
    await writeFile("test-results/microphone-capture.json", JSON.stringify({
      profile: "kt-vibecoding-python-web-v2", observations, console_errors: errors.length,
      physical_microphone: liveMicrophone ? "observed" : "not configured; no capture or transcript acceptance claimed",
      permission_prompt: "not driven; live mode grants microphone permission through the browser context",
      evidence_limits: "No speaker accuracy target, real-device interruption, denied prompt, hard-crash cleanup, or L3 owner acceptance is inferred.",
    }, null, 2), "utf8");
  } finally {
    await Promise.allSettled(pendingResponses);
    if (meetings.size) {
      await logout();
      await login(writer, secret);
      for (const id of meetings) {
        const result = await request(`/meetings/${id}`);
        if (result.status === 404) continue;
        assert.equal(result.status, 200);
        assert.ok(result.body.title.startsWith(prefix), "Only this run's meeting may be removed");
        if (!["succeeded", "cancelled"].includes(result.body.status)) await request(`/meetings/${id}/cancel`, "POST");
        const speakers = await request(`/meetings/${id}/speakers?offset=0&limit=100`);
        for (const speaker of speakers.body.items || []) if (speaker.decision === "enrolled" && speaker.profile_public_id) profiles.add(speaker.profile_public_id);
        assert.ok([204, 404].includes((await request(`/meetings/${id}`, "DELETE")).status));
      }
      for (const id of profiles) assert.ok([204, 404].includes((await request(`/speaker-profiles/${id}`, "DELETE")).status));
    }
    await logout();
  }
}, { requireCredentials: false });
