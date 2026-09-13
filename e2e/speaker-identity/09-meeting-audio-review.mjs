import { mkdir, readFile, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));

await withBrowser("meeting source audio review", async ({ page, assert }) => {
  const username = process.env.APP_E2E_AUDIO_REVIEW_USER;
  const password = process.env.APP_E2E_AUDIO_REVIEW_PASS;
  const meetingId = process.env.APP_E2E_AUDIO_REVIEW_MEETING_ID;
  assert.ok(username && password, "An ordinary meeting reader account is required");
  assert.match(meetingId || "", /^[a-f0-9-]{36}$/);
  const errors = [], mutations = [], observations = [];
  page.on("pageerror", () => errors.push("pageerror"));
  page.on("console", (message) => { if (message.type() === "error") errors.push("console_error"); });
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/") && request.method() !== "GET" && !path.endsWith("/auth/login")) mutations.push(request.method());
  });
  async function locale(value) {
    const switcher = page.getByRole("button", { name: catalogues[value === "tr" ? "en" : "tr"]["common.otherLanguage"], exact: true });
    if (await switcher.count()) await switcher.click();
  }
  async function get(path) {
    return page.evaluate(async (path) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { headers: {
        Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id,
      } });
      if (!response.ok) throw new Error("Fixture read failed");
      return response.json();
    }, path);
  }
  try {
    await page.goto(baseUrl + "/login"); await locale("tr");
    await page.getByLabel(catalogues.tr["login.username"], { exact: true }).fill(username);
    await page.getByLabel(catalogues.tr["login.password"], { exact: true }).fill(password);
    const authenticated = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
    await page.getByRole("button", { name: catalogues.tr["login.submit"], exact: true }).click();
    const login = await authenticated; assert.equal(login.status(), 200);
    const identity = (await login.json()).user;
    assert.equal(identity.is_super_admin, false);
    assert.ok(identity.permissions.includes("meeting_analysis:read"));
    assert.ok(!identity.permissions.includes("*:*"));
    await page.waitForURL(baseUrl + "/");
    const before = await get(`/meetings/${meetingId}`);
    const speakersBefore = await get(`/meetings/${meetingId}/speakers?offset=0&limit=100`);
    const textBefore = await get(`/meetings/${meetingId}/transcript?offset=0&limit=50`);
    assert.equal(before.status, "succeeded"); assert.equal(before.source_available, true);
    assert.ok(textBefore.items.length >= 2, "The fixture needs two real transcript rows");
    await page.goto(baseUrl + `/meetings/${meetingId}`);
    for (const language of ["tr", "en"]) for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 }); await locale(language);
      const text = catalogues[language];
      await page.getByRole("heading", { name: text["meeting.transcript"], exact: true }).waitFor();
      const first = page.locator("[data-transcript-id]").first();
      const button = first.getByRole("button", { name: new RegExp(text["meeting.audio.listen"]) });
      await button.focus();
      const loaded = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/audio-preview"));
      await page.keyboard.press("Enter");
      const response = await loaded; assert.equal(response.status(), 200);
      assert.equal(response.headers()["content-type"], "audio/wav");
      assert.equal(response.headers()["cache-control"], "no-store");
      assert.equal(response.headers()["x-content-type-options"], "nosniff");
      const query = new URL(response.url()).searchParams;
      const start = Number(query.get("start_seconds")), end = Number(query.get("end_seconds"));
      assert.ok(end > start && end - start <= 30 && start >= 0 && end <= before.duration_seconds);
      const bytes = await response.body(); assert.ok(bytes.length > 44 && bytes.length <= 11_520_128);
      assert.equal(bytes.subarray(0, 4).toString("ascii"), "RIFF");
      assert.equal(bytes.subarray(8, 12).toString("ascii"), "WAVE");
      const player = page.locator("audio"); await player.waitFor({ state: "visible" });
      await page.waitForFunction(() => { const audio = document.querySelector("audio"); return audio && audio.readyState >= 2 && Number.isFinite(audio.duration); });
      const media = await player.evaluate(async (element) => {
        let started = false;
        try { await element.play(); started = !element.paused; }
        catch (error) { if (error.name !== "NotAllowedError") throw error; }
        element.pause(); return { duration: element.duration, started, controls: element.controls, sourceIsBlob: element.currentSrc.startsWith("blob:") };
      });
      assert.ok(Math.abs(media.duration - (end - start)) < 0.01); assert.equal(media.controls, true); assert.equal(media.sourceIsBlob, true);
      const tree = await page.locator("body").ariaSnapshot(); assert.ok(tree.includes(text["meeting.audio.close"]));
      const dimensions = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
      assert.ok(dimensions[0] <= dimensions[1] + 1);
      await page.getByRole("button", { name: text["meeting.audio.close"], exact: true }).click();
      assert.equal(await page.locator("audio").count(), 0);
      assert.equal(await button.evaluate((element) => document.activeElement === element), true);
      observations.push({ language, width, loaded: true, decoded: true, playback_started: media.started, keyboard: true, no_overflow: true });
    }
    assert.equal(JSON.stringify(await get(`/meetings/${meetingId}`)) === JSON.stringify(before), true, "Meeting data changed");
    assert.equal(JSON.stringify(await get(`/meetings/${meetingId}/speakers?offset=0&limit=100`)) === JSON.stringify(speakersBefore), true, "Speaker data changed");
    assert.equal(JSON.stringify(await get(`/meetings/${meetingId}/transcript?offset=0&limit=50`)) === JSON.stringify(textBefore), true, "Transcript data changed");
    assert.deepEqual(errors, []); assert.deepEqual(mutations, []);
    await mkdir("test-results", { recursive: true });
    await writeFile("test-results/meeting-audio-review.json", JSON.stringify({ observations, ordinary_role: true, business_data_unchanged: true, physical_output_verified: false, model_accuracy_measured: false }, null, 2));
  } finally {
    for (const language of ["tr", "en"]) {
      const button = page.getByRole("button", { name: catalogues[language]["common.signOut"], exact: true });
      if (await button.count()) { await button.click(); break; }
    }
    assert.equal(await page.locator("audio").count(), 0);
  }
}, { requireCredentials: false });
