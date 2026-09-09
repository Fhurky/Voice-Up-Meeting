import { randomUUID } from "node:crypto";
import { access } from "node:fs/promises";
import { baseUrl, username, password, withBrowser } from "../shared/harness.mjs";

// A valid, silent PCM recording exercises a real audio-quality failure, not identity accuracy.
function silenceWav() {
  const samples = 16_000 * 4;
  const wav = Buffer.alloc(44 + samples * 2);
  wav.write("RIFF", 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write("WAVEfmt ", 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(16_000, 24); wav.writeUInt32LE(32_000, 28);
  wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write("data", 36);
  wav.writeUInt32LE(samples * 2, 40);
  return wav;
}

await withBrowser("local speaker pilot, both locales and real audio boundaries", async ({ page, assert }) => {
  const createdProfiles = [];
  const recordings = [];
  const consoleErrors = [];
  const failedRequests = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push({ url: request.url(), failure: request.failure()?.errorText }));

  async function publicRequest(path, method = "GET") {
    return page.evaluate(async ({ path, method }) => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, {
        method, headers: { Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id },
      });
      return { status: response.status, body: response.status === 204 ? null : await response.json() };
    }, { path, method });
  }

  async function awaitTerminal() {
    await page.waitForURL(/\/speaker-jobs\/[a-f0-9-]+$/);
    const id = new URL(page.url()).pathname.split("/").at(-1);
    await page.getByText(/^(Tamamlandı|Başarısız)$/).waitFor({ timeout: 330_000 });
    const response = await publicRequest("/speaker-jobs/" + id);
    assert.equal(response.status, 200);
    recordings.push(response.body.recording_public_id);
    return response.body;
  }

  try {
    await page.goto(baseUrl + "/speaker-analysis");
    await page.waitForURL(baseUrl + "/login");
    await page.getByLabel("Kullanıcı adı", { exact: true }).fill(username);
    await page.getByLabel("Parola", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
    await page.waitForURL(baseUrl + "/");
    await page.getByRole("navigation", { name: "Ana gezinme" }).getByRole("link", { name: "Sesi tanı", exact: true }).click();
    await page.getByRole("heading", { name: "Sesi tanı", exact: true }).waitFor();
    assert.ok((await page.locator("body").ariaSnapshot()).includes("Ses dosyası"));
    await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByRole("heading", { name: "Identify voice", exact: true }).waitFor();
    await page.getByText("Only one person should speak in the file.", { exact: false }).waitFor();
    await page.getByRole("button", { name: "Türkçe", exact: true }).click();

    await page.getByLabel("Ses dosyası").setInputFiles({ name: "invalid.wav", mimeType: "audio/wav", buffer: Buffer.from("RIFF0000WAVEinvalid") });
    await page.getByRole("button", { name: "Yükle ve analizi başlat" }).click();
    await page.getByRole("alert").filter({ hasText: "çözülebilir bir ses kaydı değil" }).waitFor();

    await page.getByLabel("Ses dosyası").setInputFiles({ name: "silence.wav", mimeType: "audio/wav", buffer: silenceWav() });
    await page.getByRole("button", { name: "Yükle ve analizi başlat" }).click();
    const failed = await awaitTerminal();
    assert.equal(failed.status, "failed");
    assert.equal(failed.error.code, "insufficient_speech");
    await page.getByRole("alert").filter({ hasText: "Yeterli kullanılabilir konuşma bulunamadı" }).waitFor();
    const savedUrl = page.url();
    await page.reload();
    await page.getByText("Başarısız", { exact: true }).waitFor();
    assert.equal(page.url(), savedUrl);

    const cleanAudio = process.env.APP_E2E_ENROLL_AUDIO;
    const otherAudio = process.env.APP_E2E_OTHER_AUDIO;
    assert.ok(cleanAudio, "APP_E2E_ENROLL_AUDIO must point to an explicitly supplied clean single-speaker recording with >=10 seconds usable speech; no generated fake success is permitted");
    assert.ok(otherAudio, "APP_E2E_OTHER_AUDIO must point to a clean recording of a different speaker for the wrong-target and unknown checks");
    await access(cleanAudio);
    await access(otherAudio);
    const profileName = "E2E " + randomUUID();
    await page.getByRole("navigation", { name: "Ana gezinme" }).getByRole("link", { name: "Konuşmacılar", exact: true }).click();
    await page.getByLabel("Konuşmacı adı veya takma adı").fill(profileName);
    await page.getByLabel("Ses dosyası").setInputFiles(cleanAudio);
    await page.getByRole("button", { name: "Yükle ve profil oluştur" }).click();
    const enrollment = await awaitTerminal();
    assert.equal(enrollment.status, "succeeded");
    assert.equal(enrollment.result.decision, "enrolled");
    assert.ok(enrollment.result.profile_public_id);
    createdProfiles.push(enrollment.result.profile_public_id);
    if (process.env.APP_E2E_EXPECT_DEVICE) assert.ok(enrollment.result.device.startsWith(process.env.APP_E2E_EXPECT_DEVICE));
    await page.getByRole("heading", { name: "Ses profili kaydedildi" }).waitFor();

    await page.getByRole("link", { name: "Konuşmacı profillerini gör" }).click();
    const card = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: profileName, exact: true }) });
    await card.getByRole("button", { name: "Adı değiştir" }).click();
    await page.getByRole("form", { name: "Profil adını değiştir" }).getByLabel("Konuşmacı adı veya takma adı").fill(profileName + " renamed");
    await page.getByRole("button", { name: "Kaydet", exact: true }).click();
    await page.getByRole("heading", { name: profileName + " renamed", exact: true }).waitFor();

    const renamedCard = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: profileName + " renamed", exact: true }) });
    await renamedCard.getByRole("button", { name: "Örnek ekle", exact: true }).click();
    await page.getByLabel("Ses dosyası").setInputFiles(cleanAudio);
    await page.getByRole("button", { name: "Yükle ve örneği doğrula" }).click();
    const added = await awaitTerminal();
    assert.equal(added.status, "succeeded");
    assert.equal(added.result.decision, "enrolled");
    assert.equal(added.result.profile_public_id, enrollment.result.profile_public_id);

    await page.getByRole("link", { name: "Konuşmacı profillerini gör" }).click();
    const targetCard = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: profileName + " renamed", exact: true }) });
    await targetCard.getByRole("button", { name: "Örnek ekle", exact: true }).click();
    await page.getByLabel("Ses dosyası").setInputFiles(otherAudio);
    await page.getByRole("button", { name: "Yükle ve örneği doğrula" }).click();
    const rejected = await awaitTerminal();
    assert.equal(rejected.status, "failed");
    assert.equal(rejected.error.code, "target_mismatch");
    await page.getByRole("alert").filter({ hasText: "Mevcut profil değiştirilmedi" }).waitFor();

    await page.getByRole("navigation", { name: "Ana gezinme" }).getByRole("link", { name: "Sesi tanı", exact: true }).click();
    await page.getByLabel("Ses dosyası").setInputFiles(cleanAudio);
    await page.getByRole("button", { name: "Yükle ve analizi başlat" }).click();
    const identified = await awaitTerminal();
    assert.equal(identified.status, "succeeded");
    assert.equal(identified.result.decision, "recognized");
    assert.equal(identified.result.profile_public_id, enrollment.result.profile_public_id);
    await page.getByRole("heading", { name: "Konuşmacı tanındı" }).waitFor();
    await page.getByText("Kosinüs benzerliği bir karşılaştırma puanıdır", { exact: false }).waitFor();

    await page.getByRole("navigation", { name: "Ana gezinme" }).getByRole("link", { name: "Sesi tanı", exact: true }).click();
    await page.getByLabel("Ses dosyası").setInputFiles(otherAudio);
    await page.getByRole("button", { name: "Yükle ve analizi başlat" }).click();
    const unknown = await awaitTerminal();
    assert.equal(unknown.status, "succeeded");
    assert.equal(unknown.result.decision, "unknown");
    assert.equal(unknown.result.profile_public_id, null);
    await page.getByRole("heading", { name: "Bilinmeyen konuşmacı" }).waitFor();

    await page.getByRole("navigation", { name: "Ana gezinme" }).getByRole("link", { name: "Konuşmacılar", exact: true }).click();
    const renamed = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: profileName + " renamed", exact: true }) });
    await renamed.getByText("2 / 20", { exact: true }).waitFor();
    await renamed.getByRole("button", { name: "Sil", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Profili sil", exact: true }).click();
    await page.getByRole("alertdialog").waitFor({ state: "hidden" });
    assert.equal(await page.getByRole("heading", { name: profileName + " renamed", exact: true }).count(), 0);
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failedRequests.filter((request) => request.failure !== "net::ERR_ABORTED"), []);
  } finally {
    for (const id of createdProfiles) {
      const response = await publicRequest("/speaker-profiles/" + id, "DELETE");
      assert.ok([204, 404].includes(response.status), "test profile cleanup failed");
    }
    for (const id of new Set(recordings)) {
      const response = await publicRequest("/recordings/" + id, "DELETE");
      assert.ok([204, 404].includes(response.status), "test recording cleanup failed");
    }
  }
});
