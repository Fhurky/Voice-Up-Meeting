import { mkdir, writeFile } from "node:fs/promises";
import { baseUrl, withBrowser } from "../shared/harness.mjs";
import { catalogues, get, loginReviewer, publicRequest, setLocale, signOut, suggest } from "./text-review-support.mjs";

await withBrowser("saved transcript corrections", async ({ page, assert }) => {
  const meetingId = process.env.APP_E2E_CORRECTION_SAVE_MEETING_ID;
  assert.match(meetingId || "", /^[a-f0-9-]{36}$/);
  assert.equal(process.env.APP_E2E_CORRECTION_SAVE_CONFIRM, "disposable-test-meeting", "Saving and deleting this isolated test fixture must be explicitly enabled");
  const errors = [], mutations = [], observations = [];
  let ownedFixture = false, savedRequests = 0, suggestions = 0, cleaned = false;
  page.on("pageerror", () => errors.push("pageerror"));
  page.on("console", (message) => { if (message.type() === "error") errors.push("console_error"); });
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/correction-suggestion")) suggestions += 1;
    else if (path.endsWith("/corrections") && request.method() === "POST") savedRequests += 1;
    else if (path.startsWith("/api/") && request.method() !== "GET" && !path.endsWith("/auth/login") && !(request.method() === "DELETE" && path.endsWith(`/meetings/${meetingId}`))) mutations.push(request.method());
  });
  try {
    await loginReviewer(page, assert);
    const meeting = await get(page, assert, `/meetings/${meetingId}`);
    assert.equal(meeting.status, "succeeded");
    assert.ok(meeting.title.startsWith("e2e-text-correction-"), "Only an explicitly dedicated correction test meeting may be changed or cleaned up");
    ownedFixture = true;
    const speakersBefore = await get(page, assert, `/meetings/${meetingId}/speakers?offset=0&limit=100`);
    const before = await get(page, assert, `/meetings/${meetingId}/transcript?offset=0&limit=50`);
    assert.equal(before.provisional, false);
    const selectedId = process.env.APP_E2E_CORRECTION_SAVE_TRANSCRIPT_ID;
    const turn = before.items.find((item) => (!selectedId || item.public_id === selectedId) && item.text.length > 0 && Array.from(item.text).length <= 1024);
    assert.ok(turn, "The first transcript page must contain an eligible isolated test turn");
    await page.goto(baseUrl + `/meetings/${meetingId}`);
    const { panel, result, installed, mapped } = await suggest(page, assert, turn, "tr");
    assert.ok(result.save_token && mapped > 0 && mapped === result.proposals.length, "The real model must produce an actual saveable suggestion; no fabricated fallback is allowed");
    assert.equal(suggestions, 1);
    const savedResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith(`/${turn.public_id}/corrections`));
    await panel.getByRole("button", { name: catalogues.tr["meeting.review.save"], exact: true }).click();
    const response = await savedResponse; assert.equal(response.status(), 200);
    const sent = response.request().postDataJSON();
    assert.deepEqual(Object.keys(sent), ["save_token"]);
    assert.ok(sent.save_token === result.save_token, "Save sends the exact displayed proposal proof only");
    const saved = await response.json();
    assert.equal(saved.revision, result.expected_revision + 1);
    assert.ok(saved.corrected_text === result.suggested_text, "The saved version matches the accepted visible sentence");
    assert.equal(saved.model_name, result.model_name); assert.equal(saved.model_digest, result.model_digest);
    await page.getByText(catalogues.tr["meeting.review.saved"], { exact: true }).waitFor();
    assert.equal(await page.locator("[data-text-review]").count(), 0);
    assert.equal(savedRequests, 1);
    for (const language of ["tr", "en"]) {
      await page.reload(); await setLocale(page, language);
      const row = page.locator(`[data-transcript-id="${turn.public_id}"]`);
      await row.locator("[data-corrected-text]").waitFor();
      assert.ok(await row.locator("[data-corrected-text]").textContent() === saved.corrected_text, "Reload shows the saved version");
      assert.equal(await row.locator("[data-corrected-text] ins.correction-word").count(), saved.edits.length);
      await row.getByRole("button", { name: catalogues[language]["meeting.review.originalView"], exact: true }).click();
      assert.ok(await row.locator("[data-original-text]").textContent() === turn.text, "The original remains available after saving and reloading");
      await row.getByRole("button", { name: catalogues[language]["meeting.review.correctedView"], exact: true }).click();
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        const dimensions = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
        assert.ok(dimensions[0] <= dimensions[1] + 1);
        observations.push({ language, width, installed_models: installed, saved_revision: saved.revision, green_edits: saved.edits.length, reload: true, original_toggle: true, no_overflow: true });
      }
    }
    const after = await get(page, assert, `/meetings/${meetingId}/transcript?offset=0&limit=50`);
    const sourceOnly = (list) => list.items.map(({ correction, ...item }) => item);
    assert.ok(JSON.stringify(sourceOnly(before)) === JSON.stringify(sourceOnly(after)), "Source text, timestamps and speaker links remain unchanged");
    assert.ok(JSON.stringify(speakersBefore) === JSON.stringify(await get(page, assert, `/meetings/${meetingId}/speakers?offset=0&limit=100`)), "Speaker data remains unchanged");
    const stored = after.items.find((item) => item.public_id === turn.public_id).correction;
    assert.equal(stored.public_id, saved.public_id); assert.equal(stored.revision, saved.revision);
    assert.deepEqual(errors, []); assert.deepEqual(mutations, []);
  } finally {
    if (ownedFixture) {
      const cleanup = await publicRequest(page, `/meetings/${meetingId}`, "DELETE");
      assert.ok([204, 404].includes(cleanup.status), "Public API cleanup of the dedicated test meeting failed");
      cleaned = true;
    }
    await signOut(page);
  }
  await mkdir("test-results", { recursive: true });
  await writeFile("test-results/saved-transcript-corrections.json", JSON.stringify({ observations, actual_model_requests: suggestions, save_requests: savedRequests, ordinary_role: true, source_unchanged: true, fixture_cleaned: cleaned, model_accuracy_measured: false }, null, 2));
}, { requireCredentials: false });
