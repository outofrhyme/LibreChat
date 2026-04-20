const perfEnabled =
  import.meta.env.VITE_PERF_DEBUG === 'true' || import.meta.env.VITE_PERF_DEBUG === '1';

if (typeof globalThis === 'object' && globalThis != null) {
  (globalThis as { __LIBRECHAT_PERF_DEBUG?: boolean }).__LIBRECHAT_PERF_DEBUG = perfEnabled;
}

export const logPerf = (label: string, data: Record<string, unknown> = {}) => {
  if (!perfEnabled) {
    return;
  }

  console.debug(`[perf] ${label}`, data);
};

export const isPerfEnabled = perfEnabled;
