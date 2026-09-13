import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { baseUrl } from "../shared/harness.mjs";

export const catalogues = Object.fromEntries(await Promise.all(["tr", "en"].map(async (language) => [
  language, JSON.parse(await readFile(new URL(`../../app/frontend/src/locales/${language}.json`, import.meta.url), "utf8")),
])));

export async function setLocale(page, language) {
  const switcher = page.getByRole("button", { name: catalogues[language === "tr" ? "en" : "tr"]["common.otherLanguage"], exact: true });
  if (await switcher.count()) await switcher.click();
  await page.waitForFunction((value) => document.documentElement.lang === value, language);
}

export async function loginReviewer(page, assert) {
  const username = process.env.APP_E2E_TEXT_REVIEW_USER;
  const password = process.env.APP_E2E_TEXT_REVIEW_PASS;
  assert.ok(username && password, "An ordinary meeting reader and writer account is required");
  await page.goto(baseUrl + "/login"); await setLocale(page, "tr");
  await page.getByLabel(catalogues.tr["login.username"], { exact: true }).fill(username);
  await page.getByLabel(catalogues.tr["login.password"], { exact: true }).fill(password);
  const authenticated = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login"));
  await page.getByRole("button", { name: catalogues.tr["login.submit"], exact: true }).click();
  const login = await authenticated; assert.equal(login.status(), 200);
  const identity = (await login.json()).user;
  assert.equal(identity.is_super_admin, false);
  assert.ok(identity.permissions.includes("meeting_analysis:read"));
  assert.ok(identity.permissions.includes("meeting_analysis:run"));
  assert.ok(!identity.permissions.includes("*:*"));
  await page.waitForURL(baseUrl + "/");
}

export async function publicRequest(page, path, method = "GET") {
  return page.evaluate(async ({ path, method }) => {
    const user = JSON.parse(localStorage.getItem("voiceup.user") || "null");
    const response = await fetch("/api/voiceup/v1" + path, { method, headers: {
      Authorization: "Bearer " + localStorage.getItem("voiceup.access_token"), "x-tenant-id": user.tenant_id,
    } });
    return { status: response.status, body: response.status === 204 ? null : await response.json() };
  }, { path, method });
}

export async function get(page, assert, path) {
  const response = await publicRequest(page, path); assert.equal(response.status, 200, "Public fixture read failed"); return response.body;
}

export async function signOut(page) {
  for (const language of ["tr", "en"]) {
    const button = page.getByRole("button", { name: catalogues[language]["common.signOut"], exact: true });
    if (await button.count()) { await button.click(); break; }
  }
}

export async function suggest(page, assert, turn, language) {
  const text = catalogues[language];
  const row = page.locator(`[data-transcript-id="${turn.public_id}"]`);
  if (turn.correction) await row.getByRole("button", { name: text["meeting.review.originalView"], exact: true }).click();
  const button = row.getByRole("button", { name: new RegExp(text["meeting.review.action"]) });
  const catalogResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/meetings/review-models"));
  await button.focus(); await page.keyboard.press("Enter");
  const listed = await catalogResponse; assert.equal(listed.status(), 200);
  assert.equal(listed.headers()["cache-control"], "no-store");
  const catalog = await listed.json();
  const model = process.env.APP_E2E_TEXT_REVIEW_MODEL
    ? catalog.items.find((item) => item.name === process.env.APP_E2E_TEXT_REVIEW_MODEL && item.selectable)
    : catalog.items.find((item) => item.is_default && item.selectable);
  assert.ok(model, "The requested installed model or configured default must be selectable");
  const panel = page.getByRole("region", { name: text["meeting.review.title"], exact: true });
  const select = panel.getByLabel(text["meeting.review.model"], { exact: true });
  await select.waitFor();
  assert.equal(await select.locator("option").count(), catalog.items.length + 1);
  assert.deepEqual(await select.locator("option").evaluateAll((options) => options.filter((option) => option.value).map((option) => ({ name: option.value, disabled: option.disabled }))), catalog.items.map((item) => ({ name: item.name, disabled: !item.selectable })));
  await select.selectOption(model.name);
  const reviewed = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith(`/${turn.public_id}/correction-suggestion`), { timeout: 115000 });
  await panel.getByRole("button", { name: text["meeting.review.check"], exact: true }).click();
  const response = await reviewed; assert.equal(response.status(), 200, "Actual selected local model review must succeed");
  assert.equal(response.headers()["cache-control"], "no-store");
  assert.deepEqual(response.request().postDataJSON(), { model_name: model.name, model_digest: model.digest });
  const result = await response.json();
  assert.equal(result.transcript_public_id, turn.public_id);
  assert.ok(result.original_text === turn.text, "The response must retain the exact original");
  assert.equal(result.source_text_sha256, createHash("sha256").update(turn.text).digest("hex"));
  assert.equal(result.model_name, model.name); assert.equal(result.model_digest, model.digest);
  assert.equal(result.expected_revision, turn.correction?.revision ?? 0);
  assert.equal(result.policy_version, "tr-context-words-v2");
  assert.ok(["suggested", "unchanged", "unmapped", "invalid_output"].includes(result.status));
  await page.waitForFunction(() => document.querySelector("[data-text-review]")?.getAttribute("aria-busy") === "false");
  assert.ok(await row.locator("[data-original-text]").textContent() === turn.text, "Original source remains visible");
  const mapped = result.proposals.filter((item) => item.assessment !== "unmapped");
  if (mapped.length) {
    assert.ok(await panel.locator("[data-suggested-text]").textContent() === result.suggested_text, "Mapped suggestions match the shown sentence");
    assert.equal(await panel.locator("[data-suggested-text] ins.correction-word").count(), mapped.length);
    assert.ok(await panel.locator("[data-suggested-text] ins").evaluateAll((items) => items.every((item) => getComputedStyle(item).textDecorationLine.includes("underline") && getComputedStyle(item).color !== getComputedStyle(item.parentElement).color)), "Changes have color and underline cues");
  } else assert.equal(await panel.locator("[data-suggested-text]").count(), 0);
  assert.equal(await panel.locator("[data-assessment]").count(), result.proposals.length);
  for (const [index, proposal] of result.proposals.entries()) {
    const item = panel.locator("[data-assessment]").nth(index);
    assert.equal(await item.getAttribute("data-assessment"), proposal.assessment);
    assert.ok(await item.locator("del").textContent() === proposal.original && await item.locator("ins").textContent() === proposal.replacement, "Every model proposal is shown literally");
  }
  if (result.model_output) {
    const details = panel.locator("details.model-output");
    if (!await details.evaluate((element) => element.open)) await details.locator("summary").click();
    assert.ok(await details.locator("pre").textContent() === result.model_output, "Raw output remains plain text");
  }
  assert.equal(await panel.getByRole("button", { name: text["meeting.review.save"], exact: true }).count(), result.save_token ? 1 : 0);
  return { panel, button, row, result, installed: catalog.items.length, mapped: mapped.length };
}
