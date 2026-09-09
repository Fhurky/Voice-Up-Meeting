import {
  withBrowser,
  baseUrl,
  username,
  password,
} from "../shared/harness.mjs";

await withBrowser(
  "super-admin login and protected home",
  async ({ page, assert }) => {
    await page.goto(baseUrl + "/");
    await page.waitForURL(baseUrl + "/login");

    await page.goto(baseUrl + "/login");
    await page.getByRole("button", { name: "English", exact: true }).click();
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(baseUrl + "/");
    await page.getByRole("heading", { name: "Start recognizing voices" }).waitFor();
    const session = await page.evaluate(() =>
      JSON.parse(localStorage.getItem("voiceup.user") || "null"),
    );
    assert.equal(session.is_super_admin, true);
    assert.ok(session.tenant_id);

    const missingTenant = await page.evaluate(async (apiPrefix) => {
      const token = localStorage.getItem("voiceup.access_token");
      const response = await fetch(apiPrefix + "/auth/me", {
        headers: { Authorization: "Bearer " + token },
      });
      return response.status;
    }, "/api/voiceup/v1");
    assert.equal(missingTenant, 400);

    const me = await page.evaluate(
      async ({ apiPrefix, tenantHeader }) => {
        const token = localStorage.getItem("voiceup.access_token");
        const user = JSON.parse(
          localStorage.getItem("voiceup.user") || "null",
        );
        const response = await fetch(apiPrefix + "/auth/me", {
          headers: {
            Authorization: "Bearer " + token,
            [tenantHeader]: user.tenant_id,
          },
        });
        return { status: response.status, body: await response.json() };
      },
      { apiPrefix: "/api/voiceup/v1", tenantHeader: "x-tenant-id" },
    );
    assert.equal(me.status, 200);
    assert.equal(me.body.is_super_admin, true);
    assert.equal(me.body.public_id, session.public_id);
    assert.equal(me.body.tenant_id, session.tenant_id);
    assert.ok(me.body.roles.includes("super_admin"));
    assert.ok(Array.isArray(me.body.permissions));
    assert.ok(me.body.permissions.length > 0);

    await page.reload();
    await page.waitForURL(baseUrl + "/");
    await page.getByRole("button", { name: "Çıkış yap" }).click();
    await page.waitForURL(baseUrl + "/login");
    const cleared = await page.evaluate(() => ({
      token: localStorage.getItem("voiceup.access_token"),
      user: localStorage.getItem("voiceup.user"),
    }));
    assert.deepEqual(cleared, { token: null, user: null });
  },
);
