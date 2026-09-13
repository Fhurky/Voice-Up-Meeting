import { mkdir, readFile, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";

const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (locale) => [
  locale, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${locale}.json`, import.meta.url), "utf8")),
])));

await withBrowser("modern workspace navigation and read-only permissions", async ({ page, assert }) => {
  const username = process.env.APP_E2E_WORKSPACE_USER;
  const password = process.env.APP_E2E_WORKSPACE_PASS;
  const meetingId = process.env.APP_E2E_WORKSPACE_MEETING_ID;
  assert.ok(username && password, "An ordinary workspace reader account is required");
  if (meetingId) assert.match(meetingId, /^[a-f0-9-]{36}$/);
  const failures = [];
  const requests = [];
  const observations = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") failures.push(message.text()); });
  page.on("response", (response) => {
    if (response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/")) requests.push({ method: request.method(), path });
  });

  async function setLocale(locale) {
    const switcher = page.getByRole("button", { name: catalogues[locale === "tr" ? "en" : "tr"]["common.otherLanguage"], exact: true });
    if (await switcher.count()) await switcher.click();
  }
  async function settled() {
    await page.waitForFunction(() => !document.querySelector('[aria-busy="true"]'));
  }
  async function inspectSurface(locale, viewport, route, titleKey) {
    const text = catalogues[locale];
    await page.getByRole("heading", { name: text[titleKey], exact: true, level: 1 }).waitFor();
    await settled();
    const tree = await page.locator("body").ariaSnapshot();
    assert.ok(tree.includes(text[titleKey]), "The current page heading must be exposed");
    assert.equal(await page.getByRole("main").count(), 1);
    const widths = await page.evaluate(() => ({
      content: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    assert.ok(widths.content <= widths.viewport + 1, `${route} overflows at ${viewport.width}px`);
    assert.equal(await page.getByRole("form").count(), 0, "Read-only routes must not expose upload forms");
    assert.equal(await page.getByRole("button", { name: text["common.delete"], exact: true }).count(), 0);
    const navigation = page.getByRole("navigation", { name: text["nav.main"], exact: true });
    const current = navigation.locator('[aria-current="page"]');
    assert.equal(await current.count(), 1, "Exactly one primary navigation link must be current");
    assert.equal(await current.getAttribute("href"), route);
    observations.push({ locale, width: viewport.width, route, heading: true, read_only: true, no_horizontal_overflow: true });
    await page.screenshot({ path: `test-results/workspace-${locale}-${viewport.width}-${route === "/" ? "home" : route.slice(1)}.png`, fullPage: true });
  }

  try {
    await page.goto(baseUrl + "/login");
    await page.getByLabel(catalogues.tr["login.username"], { exact: true }).fill(username);
    await page.getByLabel(catalogues.tr["login.password"], { exact: true }).fill(password);
    const loginResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
    await page.getByRole("button", { name: catalogues.tr["login.submit"], exact: true }).click();
    const login = await loginResponse;
    assert.equal(login.status(), 200);
    const identity = (await login.json()).user;
    assert.equal(identity.is_super_admin, false);
    for (const permission of ["meeting_analysis:read", "speaker_profiles:read", "speaker_analysis:read"]) {
      assert.ok(identity.permissions.includes(permission), `${permission} is required`);
    }
    for (const permission of ["*:*", "meeting_analysis:run", "speaker_profiles:write", "speaker_analysis:run"]) {
      assert.ok(!identity.permissions.includes(permission), `${permission} must be absent from the reader fixture`);
    }
    await page.waitForURL(baseUrl + "/");
    await page.reload();
    await page.getByRole("heading", { name: catalogues.tr["home.title"], exact: true, level: 1 }).waitFor();
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: catalogues.tr["workspace.skipContent"], exact: true });
    assert.equal(await skip.evaluate((element) => element === document.activeElement), true);
    await page.keyboard.press("Enter");
    assert.equal(await page.getByRole("main").evaluate((element) => element === document.activeElement), true);
    await mkdir("test-results", { recursive: true });
    const routes = [
      { path: "/", label: "nav.home", title: "home.title" },
      { path: "/meetings", label: "nav.meetings", title: "meeting.listTitle" },
      { path: "/speaker-profiles", label: "nav.profiles", title: "speaker.profiles.title" },
      { path: "/speaker-analysis", label: "nav.analysis", title: "speaker.analysis.title" },
    ];
    for (const locale of ["tr", "en"]) {
      await setLocale(locale);
      for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
        await page.setViewportSize(viewport);
        for (const route of routes) {
          const navigation = page.getByRole("navigation", { name: catalogues[locale]["nav.main"], exact: true });
          await navigation.getByRole("link", { name: catalogues[locale][route.label], exact: true }).click();
          await page.waitForURL(baseUrl + route.path);
          await inspectSurface(locale, viewport, route.path, route.title);
        }
      }
    }
    if (meetingId) {
      for (const locale of ["tr", "en"]) {
        await page.goto(baseUrl + `/meetings/${meetingId}`);
        await setLocale(locale);
        await page.locator('[data-meeting-status="succeeded"]').waitFor();
        await page.getByRole("heading", { name: catalogues[locale]["meeting.transcript"], exact: true }).waitFor();
        await page.locator("[data-transcript-id]").first().waitFor();
        await page.locator("[data-speaker-id]").first().waitFor();
        assert.ok((await page.locator("body").ariaSnapshot()).includes(catalogues[locale]["meeting.detailTitle"]));
        assert.equal(await page.getByRole("button", { name: catalogues[locale]["common.rename"], exact: true }).count(), 0);
        observations.push({ locale, route: "/meetings/existing-result", transcript_visible: true, speakers_visible: true, read_only: true });
      }
    }
    assert.deepEqual(failures, [], "Browser console and HTTP responses must be error-free");
    assert.ok(requests.every((request) => request.method === "GET" ||
      (request.method === "POST" && request.path.endsWith("/auth/login"))), "The inspection must not mutate meeting or profile data");
    await writeFile("test-results/modern-workspace.json", JSON.stringify({
      profile: "kt-vibecoding-python-web-v2", ordinary_reader: true, keyboard_skip_link: true,
      observations, console_http_failures: failures.length, api_mutations: 0,
      existing_meeting: meetingId ? "observed" : "not configured; no result inspection claimed",
      interpretation: "Presentation and access checks only; no recognition accuracy or model runtime acceptance.",
    }, null, 2), "utf8");
  } finally {
    // No fixtures are created; preserve all existing recordings and profiles.
    for (const locale of ["tr", "en"]) {
      const logout = page.getByRole("button", { name: catalogues[locale]["common.signOut"], exact: true });
      if (await logout.count()) { await logout.click(); break; }
    }
  }
}, { requireCredentials: false });
