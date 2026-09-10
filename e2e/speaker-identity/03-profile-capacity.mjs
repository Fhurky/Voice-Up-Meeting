import { baseUrl, withBrowser } from "../shared/harness.mjs";

await withBrowser("speaker profile totals without a quota and historical errors in both locales", async ({ page, assert }) => {
  const user = process.env.APP_E2E_CAPACITY_USER;
  const secret = process.env.APP_E2E_CAPACITY_PASS;
  const failedJob = process.env.APP_E2E_CAPACITY_JOB;
  assert.ok(user, "APP_E2E_CAPACITY_USER must name an ordinary writable account in an isolated tenant with at least 50 test profiles");
  assert.ok(secret, "APP_E2E_CAPACITY_PASS is required");
  assert.match(failedJob ?? "", /^[a-f0-9-]{36}$/, "APP_E2E_CAPACITY_JOB must identify an existing failed/profile_limit job in that tenant");
  const errors = [];
  const failedRequests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(request.failure()?.errorText));

  async function publicRead(path) {
    return page.evaluate(async (path) => {
      const session = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      const response = await fetch("/api/voiceup/v1" + path, {
        headers: { Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": session.tenant_id },
      });
      return { status: response.status, body: await response.json() };
    }, path);
  }

  await page.goto(baseUrl + "/speaker-profiles");
  await page.waitForURL(baseUrl + "/login");
  await page.getByLabel("Kullanıcı adı", { exact: true }).fill(user);
  await page.getByLabel("Parola", { exact: true }).fill(secret);
  await page.getByRole("button", { name: "Giriş yap", exact: true }).click();
  await page.waitForURL(baseUrl + "/");
  const session = await page.evaluate(() => JSON.parse(localStorage.getItem("voiceup.user") || "null"));
  assert.equal(session.is_super_admin, false);
  assert.ok(session.permissions.includes("speaker_profiles:write"));
  assert.ok(session.permissions.includes("speaker_analysis:run"));
  assert.ok(session.permissions.includes("speaker_analysis:read"));
  const profiles = await publicRead("/speaker-profiles?offset=0&limit=20");
  assert.equal(profiles.status, 200);
  assert.equal(Object.hasOwn(profiles.body, "max_profiles"), false);
  assert.ok(profiles.body.total >= 50);
  assert.ok(profiles.body.items.length < profiles.body.total);
  assert.ok(profiles.body.items.some((profile) => profile.sample_count < 20));
  const terminal = await publicRead("/speaker-jobs/" + failedJob);
  assert.equal(terminal.status, 200);
  assert.equal(terminal.body.status, "failed");
  assert.equal(terminal.body.error.code, "profile_limit");

  for (const locale of ["tr", "en"]) {
    if (locale === "en") await page.getByRole("button", { name: "English", exact: true }).click();
    const labels = locale === "tr" ? {
      navigation: "Ana gezinme", profiles: "Konuşmacılar", total: "Toplam profil:",
      name: "Konuşmacı adı veya takma adı", audio: "Ses dosyası",
      create: "Yükle ve profil oluştur", add: "Örnek ekle", cancel: "Vazgeç", next: "Sonraki", previous: "Önceki",
      failure: "Bu kayıt, o sırada geçerli olan profil sınırı nedeniyle reddedildi. Yeni profil oluşturulmadı. Artık yeni bir kayıt başlatabilirsiniz.",
    } : {
      navigation: "Main navigation", profiles: "Speakers", total: "Total profiles:",
      name: "Speaker name or nickname", audio: "Audio file",
      create: "Upload and create profile", add: "Add sample", cancel: "Cancel", next: "Next", previous: "Previous",
      failure: "This enrollment was rejected under the profile limit in effect at the time. No new profile was created. You can now start a new enrollment.",
    };
    await page.getByRole("navigation", { name: labels.navigation }).getByRole("link", { name: labels.profiles, exact: true }).click();
    const total = `${labels.total} ${new Intl.NumberFormat(locale).format(profiles.body.total)}`;
    await page.getByText(total, { exact: true }).waitFor();
    assert.ok((await page.locator("body").ariaSnapshot()).includes(total));
    assert.equal(await page.getByText(/Aktif profiller \/ kapasite|Active profiles \/ capacity/).count(), 0);
    assert.equal(await page.getByLabel(labels.name).isEnabled(), true);
    await page.getByLabel(labels.name).fill("E2E unsubmitted profile");
    assert.equal(await page.getByLabel(labels.name).inputValue(), "E2E unsubmitted profile");
    assert.equal(await page.getByLabel(labels.audio).isEnabled(), true);
    // An audio selection is still required; no upload or enrollment is submitted by this scenario.
    assert.equal(await page.getByRole("button", { name: labels.create }).isDisabled(), true);
    const append = page.getByRole("button", { name: labels.add, exact: true });
    const target = profiles.body.items.find((profile) => profile.sample_count < 20);
    const card = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: target.name, exact: true }) });
    assert.ok(await append.count() > 0);
    await card.getByRole("button", { name: labels.add, exact: true }).click();
    assert.equal(await page.getByLabel(labels.audio).isEnabled(), true);
    assert.equal(await page.getByLabel(labels.name).count(), 0);
    await page.getByRole("button", { name: labels.cancel, exact: true }).click();
    assert.equal(await page.getByLabel(labels.audio).isEnabled(), true);
    assert.equal(await page.getByLabel(labels.name).isEnabled(), true);
    await page.getByRole("button", { name: labels.next, exact: true }).click();
    await page.getByRole("button", { name: labels.previous, exact: true }).waitFor();
    await page.getByText(total, { exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: labels.previous }).isEnabled(), true);
    assert.equal(await page.getByLabel(labels.audio).isEnabled(), true);

    // Navigation through the app preserves the selected locale without altering stored job state.
    await page.getByRole("navigation", { name: labels.navigation }).getByRole("link", { name: locale === "tr" ? "Sesi tanı" : "Identify voice", exact: true }).click();
    const matchingLink = page.locator(`a[href="/speaker-jobs/${failedJob}"]`);
    await matchingLink.click();
    await page.getByRole("alert").filter({ hasText: labels.failure }).waitFor();
    assert.ok((await page.locator("body").ariaSnapshot()).includes(labels.failure));
  }

  assert.deepEqual(errors, []);
  assert.deepEqual(failedRequests.filter((failure) => failure !== "net::ERR_ABORTED"), []);
  const after = await publicRead("/speaker-profiles?offset=0&limit=20");
  assert.equal(after.status, 200);
  assert.deepEqual(after.body, profiles.body);
  const historicalAfter = await publicRead("/speaker-jobs/" + failedJob);
  assert.equal(historicalAfter.status, 200);
  assert.deepEqual(historicalAfter.body, terminal.body);
  // The scenario only reads supplied fixtures and selects forms; it creates no API data to clean up.
});
