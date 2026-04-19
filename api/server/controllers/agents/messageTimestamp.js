const { logger } = require('@librechat/data-schemas');

const padTimestampPart = (value) => value.toString().padStart(2, '0');

function formatTimestamp(date) {
  return (
    [
      date.getFullYear(),
      padTimestampPart(date.getMonth() + 1),
      padTimestampPart(date.getDate()),
    ].join('-') +
    ` ${[padTimestampPart(date.getHours()), padTimestampPart(date.getMinutes()), padTimestampPart(date.getSeconds())].join(':')}`
  );
}

const LEADING_MSG_TIME_PREFIX_REGEX = /^(?:\[msg_time:\s[^\]]+\]\s*)+/;

const stripLeadingMsgTimePrefixes = (text) => text.replace(LEADING_MSG_TIME_PREFIX_REGEX, '');

const getNumericPart = (lookup, key) => Number.parseInt(lookup.get(key) ?? '', 10);

function buildMessageTimestamp(clientTimezone, now = new Date()) {
  if (clientTimezone) {
    try {
      const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: clientTimezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23',
      });

      const parts = formatter.formatToParts(now);
      const lookup = new Map(parts.map((part) => [part.type, part.value]));

      const year = getNumericPart(lookup, 'year');
      const month = getNumericPart(lookup, 'month');
      const day = getNumericPart(lookup, 'day');
      const hour = getNumericPart(lookup, 'hour');
      const minute = getNumericPart(lookup, 'minute');
      const second = getNumericPart(lookup, 'second');

      const hasInvalidPart =
        !Number.isInteger(year) ||
        !Number.isInteger(month) ||
        !Number.isInteger(day) ||
        !Number.isInteger(hour) ||
        !Number.isInteger(minute) ||
        !Number.isInteger(second) ||
        month < 1 ||
        month > 12 ||
        day < 1 ||
        day > 31 ||
        hour < 0 ||
        hour > 23 ||
        minute < 0 ||
        minute > 59 ||
        second < 0 ||
        second > 59;

      if (hasInvalidPart) {
        throw new Error('Invalid timestamp parts from Intl formatter');
      }

      const stamp = `${year}-${padTimestampPart(month)}-${padTimestampPart(day)} ${padTimestampPart(hour)}:${padTimestampPart(minute)}:${padTimestampPart(second)}`;
      return `[msg_time: ${stamp} ${clientTimezone}]`;
    } catch (_error) {
      logger.debug('[AgentController] Invalid client timezone provided, using server local timezone', {
        clientTimezone,
      });
    }
  }

  const serverTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'server-local';
  return `[msg_time: ${formatTimestamp(now)} ${serverTimezone}]`;
}

function prependMessageTimestamp(text, clientTimezone, now) {
  const timestampPrefix = buildMessageTimestamp(clientTimezone, now);
  const safeOriginalText = typeof text === 'string' ? text : '';
  const sanitizedOriginalText = stripLeadingMsgTimePrefixes(safeOriginalText);
  return sanitizedOriginalText ? `${timestampPrefix}\n${sanitizedOriginalText}` : timestampPrefix;
}

module.exports = {
  buildMessageTimestamp,
  prependMessageTimestamp,
  stripLeadingMsgTimePrefixes,
};
