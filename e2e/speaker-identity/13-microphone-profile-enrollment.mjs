import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));
const liveMicrophone = process.env.APP_E2E_MICROPHONE_LIVE === "1";
const captureSeconds = Number(process.env.APP_E2E_MICROPHONE_SECONDS || "45");

await withBrowser("microphone profile enrollment controls and optional physical enrollment", async ({ page, assert }) => {
  const writer = process.env.APP_E2E_ENROLL_USER;
  const secret = process.env.APP_E2E_ENROLL_PASS;
  const reader = process.env.APP_E2E_READER_USER;
  const readerSecret = process.env.APP_E2E_READER_PASS;
  assert.ok(writer && secret && reader && readerSecret, "Ordinary speaker writer and reader credentials are required");
  assert.ok(Number.isSafeInteger(captureSeconds) && captureSeconds >= 15 && captureSeconds <= 115);
  const prefix = `E2E microphone profile ${randomUUID().slice(0, 8)}`;
  const profiles = new Set();
  const errors = [];
  const observations = [];
  const mutations = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/") && request.method() !== "GET" && !path.endsWith("/auth/login")) mutations.push({ method: request.method(), path });
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
  async function openProfiles(locale, width) {
    const text = catalogues[locale];
    await page.setViewportSize({ width, height: 900 });
    await page.goto(baseUrl + "/speaker-profiles");
    // The language switch renders with the page; wait for either locale before switching.
    await page.getByRole("heading", { name: catalogues.tr["speaker.profiles.saved"], exact: true })
      .or(page.getByRole("heading", { name: catalogues.en["speaker.profiles.saved"], exact: true })).waitFor();
    await setLocale(locale);
    await page.getByRole("heading", { name: text["speaker.profiles.saved"], exact: true }).waitFor();
    return text;
  }
  async function inspectControls(locale, width) {
    const text = await openProfiles(locale, width);
    assert.equal(await page.getByRole("group", { name: text["microphone.source"], exact: true }).count(), 0, "The enrollment panel opens on request");
    await page.getByRole("button", { name: text["speaker.profiles.create"], exact: true }).click();
    const group = page.getByRole("group", { name: text["microphone.source"], exact: true });
    const microphoneButton = group.getByRole("button", { name: text["microphone.microphoneSource"], exact: true });
    const fileButton = group.getByRole("button", { name: text["microphone.fileSource"], exact: true });
    const supported = await page.evaluate(() => globalThis.isSecureContext && Boolean(navigator.mediaDevices?.getUserMedia)
      && Boolean(navigator.storage?.getDirectory) && typeof AudioWorkletNode !== "undefined");
    assert.equal(await (supported ? microphoneButton : fileButton).getAttribute("aria-pressed"), "true", "Default source follows capability");
    await microphoneButton.click();
    const recorder = page.getByRole("region", { name: text["speaker.microphone.title"], exact: true });
    await recorder.waitFor();
    await recorder.getByText(text["speaker.microphone.guide"], { exact: true }).waitFor();
    assert.equal(await recorder.locator("blockquote").count(), 0, "The reading script waits for recording to start");
    const tree = await recorder.ariaSnapshot();
    for (const key of ["microphone.device", "microphone.duration", "microphone.level", "microphone.start", "speaker.profiles.name"]) {
      assert.ok(tree.includes(text[key]), `${key} is exposed in the accessibility tree`);
    }
    const start = recorder.getByRole("button", { name: text["microphone.start"], exact: true });
    if (supported) {
      await start.click();
      assert.equal(await recorder.getByRole("alert").textContent(), text["speaker.error.name_required"]);
      assert.equal(await recorder.getAttribute("data-recording-state"), "idle", "No capture starts without a name");
    } else {
      assert.equal(await start.isDisabled(), true);
      await recorder.getByRole("alert").waitFor();
    }
    await fileButton.click();
    await page.getByLabel(text["speaker.audio.file"], { exact: true }).waitFor();
    assert.equal(await recorder.count(), 0);
    await microphoneButton.click();
    const widths = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth }));
    assert.ok(widths.content <= widths.viewport + 1, `microphone enrollment overflows at ${width}px`);
    await mkdir("test-results", { recursive: true });
    await page.screenshot({ path: `test-results/microphone-enrollment-${locale}-${width}.png`, fullPage: true });
    observations.push({ locale, width, supported, default_source: supported ? "microphone" : "file", script_visible: true, name_required: supported });
    return supported;
  }
  async function enroll(locale) {
    const text = await openProfiles(locale, 1440);
    await page.getByRole("button", { name: text["speaker.profiles.create"], exact: true }).click();
    await page.getByRole("button", { name: text["microphone.microphoneSource"], exact: true }).click();
    const recorder = page.getByRole("region", { name: text["speaker.microphone.title"], exact: true });
    const name = `${prefix} ${locale}`;
    await recorder.getByLabel(text["speaker.profiles.name"], { exact: true }).fill(name);
    await recorder.getByRole("button", { name: text["microphone.start"], exact: true }).click();
    await page.waitForFunction((minimum) => {
      const element = document.querySelector('[data-recording-state="recording"]');
      return element && Number(element.getAttribute("data-recording-seconds")) >= minimum;
    }, captureSeconds, { timeout: (captureSeconds + 30) * 1000 });
    assert.equal(await recorder.locator("blockquote").textContent(), text["speaker.microphone.script"]);
    await recorder.getByRole("button", { name: text["speaker.microphone.stop"], exact: true }).click();
    await page.waitForFunction(() => ["succeeded", "failed", "ready"].includes(document.querySelector("[data-recording-state]")?.getAttribute("data-recording-state")),
      undefined, { timeout: 300_000 });
    const state = await recorder.getAttribute("data-recording-state");
    const listed = await request("/speaker-profiles?offset=0&limit=100");
    for (const profile of listed.body.items) if (profile.name.startsWith(prefix)) profiles.add(profile.public_id);
    observations.push({ locale, physical_capture_seconds: captureSeconds, outcome: state,
      reason: state === "succeeded" ? "enrolled" : await recorder.getByRole("alert").textContent() });
  }

  try {
    const identity = await login(writer, secret);
    for (const permission of ["speaker_profiles:write", "speaker_analysis:run", "speaker_analysis:read"]) {
      assert.ok(identity.permissions.includes(permission), `${permission} is required`);
    }
    for (const [locale, width] of [["tr", 1440], ["en", 390]]) {
      const supported = await inspectControls(locale, width);
      if (liveMicrophone) assert.equal(supported, true, "Live enrollment requires the browser's real microphone and OPFS APIs");
    }
    if (!liveMicrophone) assert.deepEqual(mutations, [], "Control inspection must create no recordings, jobs or profiles");
    else {
      // Grants permission for actual hardware; no fake input is installed. This is not human prompt evidence.
      await page.context().grantPermissions(["microphone"], { origin: new URL(baseUrl).origin });
      await enroll("tr");
    }
    await logout();
    const readIdentity = await login(reader, readerSecret);
    assert.ok(!readIdentity.permissions.includes("speaker_profiles:write"));
    for (const [locale, width] of [["tr", 1440], ["en", 390]]) {
      const text = await openProfiles(locale, width);
      assert.equal(await page.getByRole("group", { name: text["microphone.source"], exact: true }).count(), 0);
      assert.equal(await page.getByRole("button", { name: text["microphone.start"], exact: true }).count(), 0);
      await page.getByText(text["speaker.profiles.readOnly"], { exact: true }).waitFor();
      observations.push({ locale, ordinary_reader: true, enrollment_controls_absent: true });
    }
    assert.deepEqual(errors, []);
    await writeFile("test-results/microphone-enrollment.json", JSON.stringify({
      profile: "kt-vibecoding-python-web-v2", observations, console_errors: errors.length,
      physical_microphone: liveMicrophone ? "observed" : "not configured; no capture or enrollment acceptance claimed",
      permission_prompt: "not driven; live mode grants microphone permission through the browser context",
    }, null, 2), "utf8");
  } finally {
    if (profiles.size) {
      await logout();
      await login(writer, secret);
      for (const id of profiles) assert.ok([204, 404].includes((await request(`/speaker-profiles/${id}`, "DELETE")).status));
    }
    await logout();
  }
}, { requireCredentials: false });
