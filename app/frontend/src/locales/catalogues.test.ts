import { describe, expect, it } from "vitest";
import tr from "@/locales/tr.json";
import en from "@/locales/en.json";
describe("configured locale contracts", () => {
  it("provides a nonempty flat translation for every key in both locales", () => {
    expect(Object.keys(tr).sort()).toEqual(Object.keys(en).sort());
    for (const value of [...Object.values(tr), ...Object.values(en)]) expect(typeof value === "string" && value.trim().length > 0).toBe(true);
  });
});
