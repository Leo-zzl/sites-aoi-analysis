/**
 * Pure progress state-machine logic (no DOM side-effects).
 * Extracted from app.js for testability.
 */

/** @returns {{steps:Array,isRunning:boolean}} */
export function createInitialState() {
  return { steps: [], isRunning: false };
}

/**
 * Process an incoming SSE progress payload and return the updated state.
 * @param {{steps:Array,isRunning:boolean}} state
 * @param {{stage:number,message:string,detail?:string,heartbeat?:boolean}} data
 */
export function reduceProgress(state, data) {
  const { stage, message, detail, heartbeat } = data;
  if (heartbeat) return state;

  const existingIndex = state.steps.findIndex((s) => s.message === message);
  if (existingIndex >= 0) {
    const nextSteps = state.steps.map((s, idx) =>
      idx === existingIndex
        ? { ...s, stage, detail: detail ?? s.detail, status: 'doing' }
        : s
    );
    return { ...state, steps: nextSteps };
  }

  const nextSteps = state.steps.map((s) =>
    s.status === 'doing' ? { ...s, status: 'done' } : s
  );
  nextSteps.push({ stage, message, detail: detail ?? '', status: 'doing' });
  return { ...state, steps: nextSteps };
}

/** Mark every 'doing' step as 'done'. */
export function markAllDone(state) {
  return {
    ...state,
    steps: state.steps.map((s) => (s.status === 'doing' ? { ...s, status: 'done' } : s)),
  };
}

/** Mark the currently active step as error. */
export function markError(state, errorDetail) {
  const idx = state.steps.findIndex((s) => s.status === 'doing');
  if (idx < 0) return state;
  const nextSteps = state.steps.map((s, i) =>
    i === idx ? { ...s, status: 'error', detail: errorDetail } : s
  );
  return { ...state, steps: nextSteps };
}

/** Build CSS class list for a step item. */
export function stepClass(step) {
  return `log-entry ${step.status}`;
}

/** Build icon text for a step. */
export function stepIconText(step, index) {
  if (step.status === 'done') return '✓';
  if (step.status === 'error') return '!';
  return String(index + 1);
}
