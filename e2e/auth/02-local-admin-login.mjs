import { baseUrl, withBrowser } from "../shared/harness.mjs";

await withBrowser("local admin sign-in, reload and logout in both locales", async ({ page, assert }) => {
  const failures = [];
  let localAdminRequests = 0;
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.endsWith("/auth/local-admin")) {
      localAdminRequests += 1;
      assert.equal(request.method(), "POST");
      assert.equal(request.postData(), null, "local admin sign-in must not submit credentials or an actor selection");
    }
  });

  const labels = {
    tr: { admin: "Admin olarak giriş yap", username: "Kullanıcı adı", password: "Parola", home: "Sesleri tanımaya başlayın", logout: "Çıkış yap" },
    en: { admin: "Sign in as admin", username: "Username", password: "Password", home: "Start recognizing voices", logout: "Sign out" },
  };
  for (const locale of ["tr", "en"]) {
    const text = labels[locale];
    const before = localAdminRequests;
    const optionsResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/options"));
    await page.goto(baseUrl + "/login");
    const options = await optionsResponse;
    assert.equal(options.status(), 200);
    assert.deepEqual(await options.json(), { local_admin_login_enabled: true },
      "This scenario requires the enabled local development option and an eligible pre-existing administrator.");
    if (locale === "en") await page.getByRole("button", { name: "English", exact: true }).click();
    const admin = page.getByRole("button", { name: text.admin, exact: true });
    await admin.waitFor();
    assert.equal(await page.getByLabel(text.username, { exact: true }).inputValue(), "");
    assert.equal(await page.getByLabel(text.password, { exact: true }).inputValue(), "");
    assert.equal(localAdminRequests, before, "mount must not log in automatically");
    assert.ok((await page.locator("main").ariaSnapshot()).includes(text.admin));

    const loginResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/local-admin"));
    await admin.click();
    assert.equal((await loginResponse).status(), 200);
    await page.waitForURL(baseUrl + "/");
    await page.getByRole("heading", { name: text.home, exact: true }).waitFor();
    assert.equal(localAdminRequests, before + 1);
    const session = await page.evaluate(() => {
      const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
      return { hasToken: Boolean(localStorage.getItem("voiceup.access_token")), user };
    });
    assert.equal(session.hasToken, true);
    assert.equal(session.user.is_super_admin, true);
    assert.ok(session.user.tenant_id);
    assert.ok(session.user.roles.includes("super_admin"));

    const meResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/me"));
    await page.reload();
    const me = await meResponse;
    assert.equal(me.status(), 200);
    const restored = await me.json();
    assert.equal(restored.public_id, session.user.public_id);
    assert.equal(restored.tenant_id, session.user.tenant_id);
    assert.equal(restored.is_super_admin, true);
    if (locale === "en") await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByRole("heading", { name: text.home, exact: true }).waitFor();
    assert.equal(localAdminRequests, before + 1, "reload must restore through me without another login");

    await page.getByRole("button", { name: text.logout, exact: true }).click();
    await page.waitForURL(baseUrl + "/login");
    await page.getByRole("button", { name: text.admin, exact: true }).waitFor();
    assert.equal(localAdminRequests, before + 1, "logout must not trigger automatic login");
    assert.deepEqual(await page.evaluate(() => ({
      token: localStorage.getItem("voiceup.access_token"),
      user: localStorage.getItem("voiceup.user"),
    })), { token: null, user: null });
  }
  assert.deepEqual(failures, [], "browser console and HTTP responses must be error-free");
}, { requireCredentials: false });
