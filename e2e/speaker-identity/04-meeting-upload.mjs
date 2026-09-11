import { randomUUID, createHash } from "node:crypto";
import { mkdir } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

await withBrowser("meeting upload, resume and ordinary permissions in both locales", async ({ page, assert }) => {
  const writer = process.env.APP_E2E_MEETING_USER;
  const secret = process.env.APP_E2E_MEETING_PASS;
  const reader = process.env.APP_E2E_MEETING_READER_USER;
  const readerSecret = process.env.APP_E2E_MEETING_READER_PASS;
  assert.ok(writer && secret && reader && readerSecret, "Ordinary meeting writer and read-only credentials are required");
  const meetings = new Set();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  async function login(user, password) {
    await page.goto(baseUrl + "/login");
    await page.getByLabel("Kullanıcı adı", { exact: true }).fill(user);
    await page.getByLabel("Parola", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
    await page.waitForURL(baseUrl + "/");
    const identity = await page.evaluate(() => JSON.parse(localStorage.getItem("voiceup.user") || "null"));
    assert.equal(identity.is_super_admin, false);
    assert.ok(!identity.permissions.includes("*:*"));
    return identity;
  }
  async function request(path, method = "GET", body, extraHeaders = {}) {
    return page.evaluate(async ({ path, method, body, extraHeaders }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, { method,
        headers: { Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id, ...extraHeaders },
        body: Array.isArray(body) ? Uint8Array.from(body) : body,
      });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    }, { path, method, body, extraHeaders });
  }
  try {
    const identity = await login(writer, secret);
    assert.ok(identity.permissions.includes("meeting_analysis:run"));
    await page.goto(baseUrl + "/meetings");
    await page.getByLabel("Toplantı adı", { exact: true }).fill("E2E meeting " + randomUUID());
    await page.getByLabel("Toplantı ses dosyası").setInputFiles({ name: "invalid.wav", mimeType: "audio/wav", buffer: Buffer.from("invalid audio") });
    await page.getByLabel("Toplam katılımcı sayısı (isteğe bağlı)").fill("5");
    await page.getByLabel("Konuşan kişi sayısı (kesin biliniyorsa)").fill("6");
    await page.getByRole("checkbox").uncheck();
    await page.getByRole("button", { name: "Yüklemeyi başlat", exact: true }).click();
    await page.getByRole("alert").filter({ hasText: "Konuşan kişi sayısı toplam katılımcı sayısını aşamaz." }).waitFor();
    assert.equal(new URL(page.url()).pathname, "/meetings");
    await page.getByLabel("Konuşan kişi sayısı (kesin biliniyorsa)").fill("3");
    await page.getByRole("button", { name: "Yüklemeyi başlat", exact: true }).click();
    await page.waitForURL(/\/meetings\/[a-f0-9-]+$/);
    const invalidId = new URL(page.url()).pathname.split("/").at(-1); meetings.add(invalidId);
    await page.getByRole("alert").filter({ hasText: "Yalnız WAV ve FLAC kayıtları desteklenir" }).waitFor();
    const invalid = await request(`/meetings/${invalidId}`);
    assert.equal(invalid.body.status, "uploading");
    assert.equal(invalid.body.participant_count, 5); assert.equal(invalid.body.expected_speakers, 3);
    await page.reload();
    await page.getByText("Devam etmek için aynı dosyayı seçin.", { exact: false }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Yüklemeye devam et", exact: true }).isDisabled(), true);
    await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByRole("heading", { name: "Meeting result", exact: true }).waitFor();
    await page.getByText("Participant upper bound: 5 · Expected active speakers: 3", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Cancel analysis", exact: true }).click();
    await page.getByRole("alertdialog").waitFor();
    assert.equal((await request(`/meetings/${invalidId}`)).body.status, "uploading");
    await page.getByRole("button", { name: "Cancel processing", exact: true }).click();
    await page.locator('[data-meeting-status="cancelled"]').waitFor();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await page.getByText("People already saved in memory are kept", { exact: false }).waitFor();
    await page.getByRole("button", { name: "Delete meeting", exact: true }).click();
    await page.waitForURL(baseUrl + "/meetings");
    assert.equal((await request(`/meetings/${invalidId}`)).status, 404);
    meetings.delete(invalidId);

    // Real public-API setup creates an incomplete source; no response or model result is mocked.
    const buffer = Buffer.alloc(4 * 1024 * 1024 + 12, 0);
    const create = await request("/meetings", "POST", JSON.stringify({ title: "E2E resume " + randomUUID(), format: "WAV", size_bytes: buffer.length, auto_enroll: false }), { "Content-Type": "application/json", "Idempotency-Key": randomUUID() });
    assert.equal(create.status, 201);
    const resumeId = create.body.public_id; meetings.add(resumeId);
    const prefix = buffer.subarray(0, 4 * 1024 * 1024);
    const append = await request(`/meetings/${resumeId}/upload-parts/0`, "PUT", [...prefix], { "Content-Type": "application/octet-stream", "X-Chunk-SHA256": createHash("sha256").update(prefix).digest("hex") });
    assert.equal(append.status, 200); assert.equal(append.body.next_index, 1);
    await page.goto(baseUrl + `/meetings/${resumeId}`);
    await page.getByLabel("Toplantı ses dosyası").setInputFiles({ name: "source.wav", mimeType: "audio/wav", buffer: Buffer.alloc(buffer.length, 1) });
    await page.getByRole("button", { name: "Yüklemeye devam et", exact: true }).click();
    await page.getByRole("alert").filter({ hasText: "Seçilen dosya kaydedilmiş parçalarla eşleşmiyor" }).waitFor();
    assert.equal((await request(`/meetings/${resumeId}/upload-parts`)).body.next_index, 1);
    await page.getByLabel("Toplantı ses dosyası").setInputFiles({ name: "source.wav", mimeType: "audio/wav", buffer });
    await page.getByRole("button", { name: "Yüklemeye devam et", exact: true }).click();
    await page.getByRole("alert").filter({ hasText: "Yalnız WAV ve FLAC kayıtları desteklenir" }).waitFor();
    const completedParts = await request(`/meetings/${resumeId}/upload-parts`);
    assert.equal(completedParts.body.next_index, 2); assert.equal(completedParts.body.uploaded_bytes, buffer.length);
    await request(`/meetings/${resumeId}`, "DELETE"); meetings.delete(resumeId);
    await page.getByRole("button", { name: "Çıkış yap", exact: true }).click();
    const readIdentity = await login(reader, readerSecret);
    assert.ok(!readIdentity.permissions.includes("meeting_analysis:run"));
    await page.goto(baseUrl + "/meetings");
    await page.getByText("Toplantıları görüntüleyebilirsiniz.", { exact: false }).waitFor();
    assert.equal(await page.getByRole("form").count(), 0);
    assert.equal((await request("/meetings", "POST", "{}", { "Content-Type": "application/json", "Idempotency-Key": randomUUID() })).status, 403);
    await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByText("You can view meetings.", { exact: false }).waitFor();
    assert.equal(await page.getByRole("form").count(), 0);
    assert.ok((await page.locator("body").ariaSnapshot()).includes("Meetings"));
    assert.deepEqual(errors, []);
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
  } catch (failure) {
    await mkdir("test-results", { recursive: true });
    await page.screenshot({ path: "test-results/meeting-upload-before-cleanup.png", fullPage: true });
    console.error("Meeting upload failure alerts:", await page.getByRole("alert").allTextContents());
    throw failure;
  } finally {
    if (meetings.size) {
      await page.goto(baseUrl + "/login");
      if (await page.getByLabel("Kullanıcı adı", { exact: true }).count()) await login(writer, secret);
      for (const id of meetings) assert.ok([204, 404].includes((await request(`/meetings/${id}`, "DELETE")).status));
    }
  }
}, { requireCredentials: false });
