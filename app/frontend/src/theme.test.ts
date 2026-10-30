import { describe, expect, it } from "vitest";
import css from "@/globals.css?raw";

const root = css.slice(css.indexOf(":root {"), css.indexOf("}", css.indexOf(":root {")));
const tokens = Object.fromEntries([...root.matchAll(/(--color-[a-z-]+):\s*(#[0-9a-fA-F]{6});/g)].map(([, name, value]) => [name, value.toLowerCase()]));

function luminance(hex: string) {
  const [red, green, blue] = [1, 3, 5].map((index) => {
    const channel = Number.parseInt(hex.slice(index, index + 2), 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}
function contrast(foreground: string, background: string) {
  const [light, dark] = [luminance(tokens[foreground]), luminance(tokens[background])].sort((first, second) => second - first);
  return (light + 0.05) / (dark + 0.05);
}

describe("institutional visual theme tokens", () => {
  it("uses the observed green, blue, orange and navy palette and no violet accent", () => {
    expect(tokens).toMatchObject({
      "--color-brand": "#43b02a", "--color-primary": "#2d7864", "--color-primary-hover": "#0e503e",
      "--color-info": "#2c7aa1", "--color-accent": "#ed6b2c", "--color-sidebar": "#0d1b2a", "--color-foreground": "#0d1b2a",
    });
    expect(css).not.toMatch(/#6942d9|#5733bd|#b8a0ff/i);
  });

  it.each([
    ["--color-foreground", "--color-background"], ["--color-foreground", "--color-surface"],
    ["--color-muted", "--color-surface"], ["--color-muted", "--color-background"],
    ["--color-primary", "--color-surface"], ["--color-primary", "--color-background"], ["--color-primary", "--color-primary-soft"],
    ["--color-surface", "--color-primary"], ["--color-surface", "--color-primary-hover"],
    ["--color-info", "--color-surface"], ["--color-info", "--color-background"],
    ["--color-notice", "--color-notice-soft"], ["--color-success", "--color-success-soft"],
    ["--color-danger", "--color-danger-soft"], ["--color-surface", "--color-danger"],
    ["--color-on-dark", "--color-sidebar"], ["--color-sidebar-muted", "--color-sidebar"], ["--color-on-dark", "--color-sidebar-active"],
    ["--color-accent-light", "--color-sidebar"], ["--color-accent", "--color-sidebar"], ["--color-sidebar", "--color-on-dark"],
    ["--color-avatar-blue-text", "--color-avatar-blue"], ["--color-avatar-rose-text", "--color-avatar-rose"],
    ["--color-avatar-sand-text", "--color-avatar-sand"],
  ])("keeps text %s on %s at 4.5:1 or more", (foreground, background) => {
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(4.5);
  });

  it("defines colour values only in the root token block", () => {
    const rules = css.slice(css.indexOf("}", css.indexOf(":root {")));
    expect(rules.match(/#[0-9a-f]{3,8}\b|rgba?\(/gi)).toBeNull();
  });

  it("keeps the orange accent at 3:1 as a component on light surfaces and the bright brand green decorative", () => {
    expect(contrast("--color-accent", "--color-surface")).toBeGreaterThanOrEqual(3);
    expect(contrast("--color-brand", "--color-surface")).toBeLessThan(3);
    const ruleBody = css.slice(css.indexOf("}", css.indexOf(":root {")));
    for (const declaration of ruleBody.match(/[a-z-]+:[^;{}]*var\(--color-brand\)[^;{}]*/g) ?? []) {
      expect(declaration).not.toMatch(/^color:|^border-color:|^outline/);
    }
  });
});
