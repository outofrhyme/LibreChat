const {
  buildMessageTimestamp,
  getCleanOriginalText,
  prependMessageTimestamp,
  stripLeadingMsgTimePrefixes,
} = require('./messageTimestamp');

describe('messageTimestamp', () => {
  it('builds a deterministic timestamp with a valid client timezone', () => {
    const stamp = buildMessageTimestamp('America/Los_Angeles', new Date('2026-05-06T12:34:56Z'));

    expect(stamp).toBe('[msg_time: 2026-05-06 05:34:56 America/Los_Angeles]');
  });

  it('strips stale prefixes before prepending a fresh one', () => {
    const text = prependMessageTimestamp(
      '[msg_time: 2026-05-05 01:02:03 America/Los_Angeles]\nhello',
      'UTC',
      new Date('2026-05-06T12:34:56Z'),
    );

    expect(text).toBe('[msg_time: 2026-05-06 12:34:56 UTC]\nhello');
  });

  it('does not create timestamp-only text for empty submissions', () => {
    expect(prependMessageTimestamp('', 'UTC', new Date('2026-05-06T12:34:56Z'))).toBe('');
    expect(prependMessageTimestamp(undefined, 'UTC', new Date('2026-05-06T12:34:56Z'))).toBe('');
    expect(
      prependMessageTimestamp(
        '[msg_time: 2026-05-05 01:02:03 UTC]\n   ',
        'UTC',
        new Date('2026-05-06T12:34:56Z'),
      ),
    ).toBe('');
  });

  it('returns clean original text for title generation', () => {
    expect(
      getCleanOriginalText(
        '[msg_time: 2026-05-05 01:02:03 UTC]\n[msg_time: 2026-05-06 01:02:03 UTC]\nhello',
      ),
    ).toBe('hello');
  });

  it('strips multiple leading prefixes', () => {
    expect(
      stripLeadingMsgTimePrefixes(
        '[msg_time: 2026-05-05 01:02:03 UTC]\n[msg_time: 2026-05-06 01:02:03 UTC]\nhello',
      ),
    ).toBe('hello');
  });
});
