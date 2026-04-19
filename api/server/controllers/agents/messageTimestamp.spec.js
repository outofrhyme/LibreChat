jest.mock(
  '@librechat/data-schemas',
  () => ({
    logger: {
      debug: jest.fn(),
    },
  }),
  { virtual: true },
);

const {
  buildMessageTimestamp,
  prependMessageTimestamp,
  stripLeadingMsgTimePrefixes,
} = require('./messageTimestamp');

describe('message timestamp prefix helpers', () => {
  test('strips all leading msg_time prefixes from edited message text', () => {
    const editedText =
      '[msg_time: 2026-04-18 23:59:59 UTC]\n[msg_time: 2026-04-19 00:00:30 UTC]\nhello world';

    expect(stripLeadingMsgTimePrefixes(editedText)).toBe('hello world');
  });

  test('prepends a single fresh prefix during resubmit/edit even if stale prefixes exist', () => {
    const now = new Date('2026-04-19T05:03:04.000Z');
    const editedText =
      '[msg_time: 2026-04-19 00:01:02 UTC]\n[msg_time: 2026-04-19 00:02:03 UTC]\nEdited question';

    const result = prependMessageTimestamp(editedText, 'UTC', now);

    expect(result).toBe('[msg_time: 2026-04-19 05:03:04 UTC]\nEdited question');
    expect(result.match(/\[msg_time:/g)).toHaveLength(1);
  });

  test('builds hour using 24-hour h23 range for timezone format', () => {
    const now = new Date('2026-04-19T00:03:04.000Z');
    const result = buildMessageTimestamp('UTC', now);

    expect(result).toContain(' 00:03:04 UTC]');
    expect(result).not.toContain(' 24:03:04 UTC]');
  });
});
