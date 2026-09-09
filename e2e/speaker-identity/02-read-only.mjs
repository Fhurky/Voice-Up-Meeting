import { baseUrl, withBrowser } from "../shared/harness.mjs";

await withBrowser("speaker pilot read-only permission surfaces", async ({ page, assert }) => {
  const reader = process.env.APP_E2E_READER_USER;
  const secret = process.env.APP_E2E_READER_PASS;
  assert.ok(reader, "APP_E2E_READER_USER must name an ordinary account with only speaker_profiles:read and speaker_analysis:read");
  assert.ok(secret, "APP_E2E_READER_PASS is required");
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(baseUrl + "/login");
  await page.getByLabel("Kullanıcı adı", { exact: true }).fill(reader);
  await page.getByLabel("Parola", { exact: true }).fill(secret);
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
  await page.waitForURL(baseUrl + "/");
  const session = await page.evaluate(() => JSON.parse(localStorage.getItem("voiceup.user") || "null"));
  assert.equal(session.is_super_admin, false);
  assert.ok(!session.permissions.includes("speaker_profiles:write"));
  assert.ok(!session.permissions.includes("speaker_analysis:run"));
  assert.ok(!session.permissions.includes("*:*"));

  await page.getByRole("navigation", { name: "Ana gezinme" }).getByRole("link", { name: "Konuşmacılar", exact: true }).click();
  await page.getByRole("heading", { name: "Konuşmacılar", exact: true }).waitFor();
  await page.getByText("Profilleri görüntüleyebilirsiniz.", { exact: false }).waitFor();
  assert.equal(await page.getByLabel("Ses dosyası").count(), 0);
  assert.equal(await page.getByRole("button", { name: "Örnek ekle", exact: true }).count(), 0);
  assert.equal(await page.getByRole("button", { name: "Sil", exact: true }).count(), 0);
  assert.ok((await page.locator("body").ariaSnapshot()).includes("Konuşmacılar"));

  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.getByRole("heading", { name: "Speakers", exact: true }).waitFor();
  await page.getByText("You can view profiles.", { exact: false }).waitFor();
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Identify voice", exact: true }).click();
  await page.getByRole("heading", { name: "Identify voice", exact: true }).waitFor();
  await page.getByText("You can view analyses.", { exact: false }).waitFor();
  assert.equal(await page.getByLabel("Audio file").count(), 0);
  await page.getByRole("button", { name: "Türkçe", exact: true }).click();
  await page.getByText("Analizleri görüntüleyebilirsiniz.", { exact: false }).waitFor();
  await page.reload();
  await page.getByRole("heading", { name: "Sesi tanı", exact: true }).waitFor();
  assert.equal(await page.getByLabel("Ses dosyası").count(), 0);
  assert.deepEqual(errors, []);
  await page.getByRole("button", { name: "Çıkış yap", exact: true }).click();
  await page.waitForURL(baseUrl + "/login");
});
