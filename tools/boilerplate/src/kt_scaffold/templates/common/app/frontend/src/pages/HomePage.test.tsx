import {describe, expect, it} from 'vitest';
describe('platform home', () => {
  it('does not ship a generic business resource', () => {
    expect(@@PROJECT_INTENT_JSON@@).not.toMatch(/sample item/i);
  });
});
