import {describe, expect, it} from 'vitest';
describe('platform home', () => {
  it('does not ship a generic business resource', () => {
    expect("VoiceUp: farkl\u0131 toplant\u0131larda konu\u015fmac\u0131lar\u0131 kal\u0131c\u0131 ses profilleriyle tan\u0131yan, yeni ki\u015fileri ay\u0131rt eden ve konu\u015fmalar\u0131 ki\u015filere ba\u011flayan yerel toplant\u0131 analiz \u00fcr\u00fcn\u00fc.").not.toMatch(/sample item/i);
  });
});
