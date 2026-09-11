import { randomUUID } from "node:crypto";
import { access } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

await withBrowser("real meeting transcript and five-to-six speaker memory", async ({ page, assert }) => {
  const sources = ["A", "B", "D", "C"].map((letter) => process.env[`APP_E2E_MEETING_AUDIO_${letter}`]);
  assert.ok(process.env.APP_E2E_MEETING_USER && process.env.APP_E2E_MEETING_PASS, "Ordinary meeting writer credentials are required");
  assert.ok(sources.every(Boolean), "Real A (five), B (same five), D (five plus short new voice), C (six eligible voices) recordings are required");
  for (const source of sources) await access(source);
  const meetings = new Set();
  const profiles = new Set();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  async function request(path, method = "GET") {
    return page.evaluate(async ({ path, method }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { method, headers: {
        Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id,
      } });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    }, { path, method });
  }
  async function upload(source, count, label) {
    await page.goto(baseUrl + "/meetings");
    // Pin interaction labels even if locale persistence is introduced later.
    const turkish = page.getByRole("button", { name: "Türkçe", exact: true });
    if (await turkish.count()) await turkish.click();
    await page.getByLabel("Toplantı adı", { exact: true }).fill(`E2E ${label} ${randomUUID()}`);
    await page.getByLabel("Toplantı ses dosyası").setInputFiles(source);
    await page.getByLabel("Konuşma dili", { exact: true }).selectOption("en");
    await page.getByLabel("Toplam katılımcı sayısı (isteğe bağlı)").fill(String(count));
    await page.getByLabel("Konuşan kişi sayısı (kesin biliniyorsa)").fill(String(count));
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Yüklemeyi başlat", exact: true }).click();
    await page.waitForURL(/\/meetings\/[a-f0-9-]+$/);
    const id = new URL(page.url()).pathname.split("/").at(-1); meetings.add(id);
    await page.locator('[data-meeting-status="succeeded"], [data-meeting-status="failed"]').waitFor({ timeout: 1_200_000 });
    const result = await request(`/meetings/${id}`);
    const speakers = await request(`/meetings/${id}/speakers?offset=0&limit=100`);
    for (const speaker of speakers.body.items) if (speaker.profile_public_id) profiles.add(speaker.profile_public_id);
    assert.equal(result.status, 200); assert.equal(result.body.status, "succeeded", "The real model job must succeed");
    assert.equal(result.body.count_mismatch, false);
    assert.equal(speakers.body.total, count);
    const transcript = await request(`/meetings/${id}/transcript?offset=0&limit=100`);
    assert.equal(transcript.body.provisional, false);
    assert.ok(transcript.body.items.some((turn) => turn.text.trim().length > 0));
    await page.locator("[data-transcript-id]").first().waitFor();
    return { id, speakers: speakers.body.items };
  }
  async function total() { return (await request("/speaker-profiles?offset=0&limit=20")).body.total; }
  try {
    await page.goto(baseUrl + "/login");
    await page.getByLabel("Kullanıcı adı", { exact: true }).fill(process.env.APP_E2E_MEETING_USER);
    await page.getByLabel("Parola", { exact: true }).fill(process.env.APP_E2E_MEETING_PASS);
    await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
    await page.waitForURL(baseUrl + "/");
    const identity = await page.evaluate(() => JSON.parse(localStorage.getItem("voiceup.user") || "null"));
    assert.equal(identity.is_super_admin, false); assert.ok(identity.permissions.includes("meeting_analysis:run"));
    assert.equal(await total(), 0, "Use an explicitly empty, isolated fixture tenant");
    const first = await upload(sources[0], 5, "first");
    assert.ok(first.speakers.every((speaker) => speaker.decision === "enrolled" && speaker.profile_public_id));
    const initialIds = first.speakers.map((speaker) => speaker.profile_public_id).sort();
    assert.equal(new Set(initialIds).size, 5); assert.equal(await total(), 5);
    const names = new Map();
    for (const [index, speaker] of first.speakers.entries()) {
      const name = `E2E person ${index + 1}`;
      const card = page.locator(`[data-speaker-id="${speaker.public_id}"]`);
      await card.getByRole("button", { name: "Adı değiştir", exact: true }).click();
      await page.getByRole("textbox", { name: "Konuşmacı adı", exact: true }).fill(name);
      await page.getByRole("button", { name: "Kaydet", exact: true }).click();
      await card.getByRole("heading", { name, exact: true }).waitFor();
      names.set(speaker.profile_public_id, name);
    }
    await page.reload();
    for (const name of names.values()) await page.getByRole("heading", { name, exact: true }).waitFor();
    await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByRole("heading", { name: "Transcript", exact: true }).waitFor();
    assert.ok((await page.locator("body").ariaSnapshot()).includes("New person saved in memory"));
    const returning = await upload(sources[1], 5, "returning");
    assert.deepEqual(returning.speakers.map((speaker) => speaker.profile_public_id).sort(), initialIds);
    assert.ok(returning.speakers.every((speaker) => speaker.decision === "recognized" && speaker.profile_name === names.get(speaker.profile_public_id)));
    assert.equal(await total(), 5);
    const short = await upload(sources[2], 6, "short-new-person");
    const pending = short.speakers.filter((speaker) => !speaker.profile_public_id);
    assert.equal(pending.length, 1); assert.equal(pending[0].decision, "profile_pending"); assert.equal(await total(), 5);
    await page.getByText("Hafızaya kaydedilmedi", { exact: true }).waitFor();
    const sixth = await upload(sources[3], 6, "sixth");
    const newPeople = sixth.speakers.filter((speaker) => !initialIds.includes(speaker.profile_public_id));
    assert.equal(newPeople.length, 1); assert.equal(newPeople[0].decision, "enrolled");
    assert.deepEqual(sixth.speakers.filter((speaker) => initialIds.includes(speaker.profile_public_id)).map((speaker) => speaker.profile_public_id).sort(), initialIds);
    assert.equal(await total(), 6);
    const retry = await request(`/meetings/${sixth.id}/retry`, "POST");
    assert.equal(retry.status, 202); assert.equal(retry.body.public_id, sixth.id); assert.equal(await total(), 6);
    assert.deepEqual(errors, []);
  } finally {
    // Only this run's meeting/profile IDs in the explicitly empty test tenant are removed.
    for (const id of meetings) assert.ok([204, 404].includes((await request(`/meetings/${id}`, "DELETE")).status));
    for (const id of profiles) assert.ok([204, 404].includes((await request(`/speaker-profiles/${id}`, "DELETE")).status));
    if (await page.getByRole("button", { name: "Çıkış yap", exact: true }).count()) await page.getByRole("button", { name: "Çıkış yap", exact: true }).click();
  }
}, { requireCredentials: false });
