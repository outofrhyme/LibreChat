const { logger } = require('@librechat/data-schemas');

const enabled =
  process.env.LIBRECHAT_PERF_DEBUG === 'true' || process.env.LIBRECHAT_PERF_DEBUG === '1';

const now = () => Number(process.hrtime.bigint() / 1000000n);

const createPerfTracker = ({ runId, userId, conversationId, endpoint }) => {
  const startMs = now();
  const marks = new Map();

  const baseMeta = {
    runId,
    userId,
    conversationId,
    endpoint,
  };

  const mark = (label, extra = {}) => {
    const ts = now();
    const sinceStartMs = ts - startMs;
    marks.set(label, ts);
    if (!enabled) {
      return;
    }
    logger.info(`[perf] ${label}`, {
      ...baseMeta,
      ...extra,
      sinceStartMs,
      ts,
    });
  };

  const span = (labelA, labelB) => {
    const a = marks.get(labelA);
    const b = marks.get(labelB);
    if (typeof a !== 'number' || typeof b !== 'number') {
      return null;
    }
    return b - a;
  };

  const summary = (extra = {}) => {
    const totalMs = now() - startMs;
    const payload = {
      ...baseMeta,
      ...extra,
      totalMs,
      spans: {
        toFirstToolCallMs: span('request.received', 'tool.first_call_start'),
        toFirstModelCallMs: span('request.received', 'model.first_call_start'),
        toFirstTokenMs: span('request.received', 'stream.first_token_forwarded'),
        streamStartupMs: span('model.first_call_start', 'stream.first_token_forwarded'),
      },
    };
    if (enabled) {
      logger.info('[perf] request.summary', payload);
    }
    return payload;
  };

  return { enabled, now, mark, span, summary };
};

module.exports = {
  createPerfTracker,
};
