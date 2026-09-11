import { mkdir, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

await withBrowser("completed meeting abstention reflects actual results", async ({ page, assert }) => {
  const user = process.env.APP_E2E_MEETING_OBSERVATION_USER;
  const password = process.env.APP_E2E_MEETING_OBSERVATION_PASS;
  const id = process.env.APP_E2E_MEETING_OBSERVATION_ID;
  const count = Number(process.env.APP_E2E_MEETING_OBSERVATION_TRACKS);
  const gallery = Number(process.env.APP_E2E_MEETING_OBSERVATION_GALLERY);
  assert.ok(user && password && /^[a-f0-9-]{36}$/.test(id || ""));
  assert.ok(Number.isInteger(count) && count > 0 && count <= 20);
  assert.equal(gallery, 0, "This read-only fixture contains pending speakers and no saved profiles");
  const errors = [], requests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) requests.push({ method: request.method(), path: url.pathname });
  });
  async function get(path) {
    return page.evaluate(async (path) => {
      const identity = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { headers: {
        Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": identity.tenant_id,
      } });
      if (!response.ok) throw new Error("Observation HTTP " + response.status);
      return response.json();
    }, path);
  }
  try {
    await page.goto(baseUrl + "/login");
    await page.getByLabel("Kullanıcı adı", { exact: true }).fill(user);
    await page.getByLabel("Parola", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
    await page.waitForURL(baseUrl + "/");
    const identity = await page.evaluate(() => JSON.parse(localStorage.getItem("voiceup.user") || "null"));
    assert.equal(identity.is_super_admin, false);
    assert.ok(identity.permissions.includes("meeting_analysis:read"));
    const before = await get(`/meetings/${id}`);
    const speakers = await get(`/meetings/${id}/speakers?offset=0&limit=100`);
    const profiles = await get("/speaker-profiles?offset=0&limit=20");
    assert.equal(before.status, "succeeded");
    assert.equal(before.observed_speakers, count); assert.equal(speakers.total, count);
    assert.equal(profiles.total, gallery);
    assert.ok(speakers.items.every((speaker) => speaker.decision === "profile_pending" && speaker.profile_public_id === null));
    await page.goto(baseUrl + `/meetings/${id}`);
    await page.locator('[data-meeting-status="succeeded"]').waitFor();
    await page.getByRole("heading", { name: "Toplantı sonucu", exact: true }).waitFor();
    await page.getByText("Ayırt edilen konuşmacı", { exact: true }).locator("..").getByText(String(count), { exact: true }).waitFor();
    await page.getByText("Hafızaya kaydedilmedi", { exact: true }).first().waitFor();
    assert.equal(await page.getByText("Hafızaya kaydedilmedi", { exact: true }).count(), count);
    assert.equal(await page.locator("[data-speaker-id]").count(), count);
    assert.equal(speakers.items[0].ordinal, 0);
    await page.getByRole("heading", { name: "Konuşmacı 1", exact: true }).waitFor();
    await page.getByRole("heading", { name: `Konuşmacı ${count}`, exact: true }).waitFor();
    assert.equal(await page.getByText("Konuşmacı 0", { exact: true }).count(), 0);
    assert.ok((await page.locator("body").ariaSnapshot()).includes("Tamamlandı"));
    await mkdir("test-results", { recursive: true });
    await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByRole("heading", { name: "Meeting result", exact: true }).waitFor();
    await page.getByText("Detected speakers", { exact: true }).locator("..").getByText(String(count), { exact: true }).waitFor();
    assert.equal(await page.getByText("Not saved in memory", { exact: true }).count(), count);
    await page.getByRole("heading", { name: "Speaker 1", exact: true }).waitFor();
    await page.getByRole("heading", { name: `Speaker ${count}`, exact: true }).waitFor();
    assert.equal(await page.getByText("Speaker 0", { exact: true }).count(), 0);
    assert.ok((await page.locator("body").ariaSnapshot()).includes("Completed"));
    const after = await get(`/meetings/${id}`);
    assert.deepEqual(after, before);
    assert.deepEqual(await get(`/meetings/${id}/speakers?offset=0&limit=100`), speakers);
    assert.equal((await get("/speaker-profiles?offset=0&limit=20")).total, gallery);
    assert.deepEqual(errors, []);
    assert.ok(requests.every((request) => request.method === "GET" || (request.method === "POST" && request.path.endsWith("/auth/login"))));
    await writeFile("test-results/meeting-observation.json", JSON.stringify({
      meeting_public_id: id, status: before.status, duration_seconds: before.duration_seconds,
      observed_speakers: count, pending_speakers: speakers.total, gallery_total: gallery,
      count_hint_provided: before.expected_speakers !== null, count_mismatch: before.count_mismatch,
      locale_checks: ["tr", "en"], ordinary_role: true, data_unchanged: true,
      interpretation: "UI reflects the existing result; this does not establish correct speaker separation or successful memory enrollment.",
    }, null, 2), "utf8");
  } finally {
    // Read-only inspection: preserve this recorded model failure and all existing profiles.
    for (const name of ["Sign out", "Çıkış yap"]) {
      const button = page.getByRole("button", { name, exact: true });
      if (await button.count()) { await button.click(); break; }
    }
  }
}, { requireCredentials: false });
