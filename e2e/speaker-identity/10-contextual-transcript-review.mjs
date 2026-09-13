import { mkdir, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";
import { catalogues, get, loginReviewer, setLocale, signOut, suggest } from "./text-review-support.mjs";

await withBrowser("contextual transcript review", async ({ page, assert }) => {
  const meetingId = process.env.APP_E2E_TEXT_REVIEW_MEETING_ID;
  assert.match(meetingId || "", /^[a-f0-9-]{36}$/);
  const errors = [], mutations = [], observations = [];
  let suggestions = 0;
  page.on("pageerror", () => errors.push("pageerror"));
  page.on("console", (message) => { if (message.type() === "error") errors.push("console_error"); });
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/correction-suggestion")) suggestions += 1;
    else if (path.startsWith("/api/") && request.method() !== "GET" && !path.endsWith("/auth/login")) mutations.push(request.method());
  });
  try {
    await loginReviewer(page, assert);
    const before = await get(page, assert, `/meetings/${meetingId}`);
    const speakersBefore = await get(page, assert, `/meetings/${meetingId}/speakers?offset=0&limit=100`);
    const textBefore = await get(page, assert, `/meetings/${meetingId}/transcript?offset=0&limit=50`);
    assert.equal(before.status, "succeeded"); assert.equal(textBefore.provisional, false);
    const turn = textBefore.items.find((item) => item.text.length > 0 && Array.from(item.text).length <= 1024);
    assert.ok(turn, "The first transcript page needs one eligible stored turn");
    await page.goto(baseUrl + `/meetings/${meetingId}`);
    for (const [index, language] of ["tr", "en"].entries()) {
      await setLocale(page, language); const text = catalogues[language];
      const { panel, button, result, installed, mapped } = await suggest(page, assert, turn, language);
      assert.equal(suggestions, index + 1, "Opening and selecting a model must not trigger extra inference");
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        const tree = await panel.ariaSnapshot(); assert.ok(tree.includes(text["meeting.review.close"]));
        const dimensions = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
        assert.ok(dimensions[0] <= dimensions[1] + 1);
        observations.push({ language, width, status: result.status, installed_models: installed, mapped, proposals: result.proposals.length, keyboard: true, source_bound: true, no_overflow: true });
      }
      await panel.getByRole("button", { name: text["meeting.review.close"], exact: true }).click();
      assert.equal(await page.locator("[data-text-review]").count(), 0);
      assert.equal(await button.evaluate((element) => document.activeElement === element), true);
    }
    assert.ok(JSON.stringify(await get(page, assert, `/meetings/${meetingId}`)) === JSON.stringify(before), "Meeting data changed");
    assert.ok(JSON.stringify(await get(page, assert, `/meetings/${meetingId}/speakers?offset=0&limit=100`)) === JSON.stringify(speakersBefore), "Speaker data changed");
    assert.ok(JSON.stringify(await get(page, assert, `/meetings/${meetingId}/transcript?offset=0&limit=50`)) === JSON.stringify(textBefore), "Transcript data changed");
    assert.deepEqual(errors, []); assert.deepEqual(mutations, []);
    await mkdir("test-results", { recursive: true });
    await writeFile("test-results/contextual-transcript-review.json", JSON.stringify({ observations, actual_model_requests: suggestions, ordinary_role: true, business_data_unchanged: true, model_accuracy_measured: false }, null, 2));
  } finally {
    await signOut(page);
    assert.equal(await page.locator("[data-text-review]").count(), 0);
  }
}, { requireCredentials: false });
