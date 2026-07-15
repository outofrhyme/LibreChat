import { stripMsgTimePrefixForDisplay } from './messageText';

describe('stripMsgTimePrefixForDisplay', () => {
  it('strips a leading timestamp prefix from user messages', () => {
    expect(
      stripMsgTimePrefixForDisplay('[msg_time: 2026-07-15 04:30:00 America/New_York]\nhello', true),
    ).toBe('hello');
  });

  it('strips a leading timestamp prefix followed by a single space from user messages', () => {
    expect(
      stripMsgTimePrefixForDisplay('[msg_time: 2026-07-15 04:30:00 America/New_York] hello', true),
    ).toBe('hello');
  });

  it('does not strip assistant messages', () => {
    const text = '[msg_time: 2026-07-15 04:30:00 America/New_York]\nhello';

    expect(stripMsgTimePrefixForDisplay(text, false)).toBe(text);
  });

  it('does not strip non-leading timestamp-like text', () => {
    const text = 'hello\n[msg_time: 2026-07-15 04:30:00 America/New_York]';

    expect(stripMsgTimePrefixForDisplay(text, true)).toBe(text);
  });
});
