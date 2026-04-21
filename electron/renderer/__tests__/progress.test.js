import { describe, it, expect } from 'vitest';
import {
  createInitialState,
  reduceProgress,
  markAllDone,
  markError,
  stepClass,
  stepIconText,
} from '../progressState.js';

describe('createInitialState', () => {
  it('returns empty steps and isRunning=false', () => {
    const s = createInitialState();
    expect(s.steps).toEqual([]);
    expect(s.isRunning).toBe(false);
  });
});

describe('reduceProgress', () => {
  it('appends a new doing step when message is new', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 10, message: '加载 AOI', detail: '读取中' });
    expect(state.steps).toHaveLength(1);
    expect(state.steps[0]).toMatchObject({ stage: 10, message: '加载 AOI', detail: '读取中', status: 'doing' });
  });

  it('marks previous doing step as done when a new message arrives', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 10, message: '加载 AOI', detail: '' });
    state = reduceProgress(state, { stage: 30, message: '加载站点', detail: '' });
    expect(state.steps[0].status).toBe('done');
    expect(state.steps[1].status).toBe('doing');
  });

  it('updates detail on existing step without adding a new one', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 10, message: '加载 AOI', detail: '读取中' });
    state = reduceProgress(state, { stage: 15, message: '加载 AOI', detail: '已识别 5 个 AOI' });
    expect(state.steps).toHaveLength(1);
    expect(state.steps[0].detail).toBe('已识别 5 个 AOI');
    expect(state.steps[0].stage).toBe(15);
  });

  it('ignores heartbeat events', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 10, message: '加载 AOI', detail: '', heartbeat: true });
    expect(state.steps).toHaveLength(0);
  });

  it('handles 2 done + 1 doing + 2 pending scenario', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 10, message: '步骤1', detail: '' });
    state = reduceProgress(state, { stage: 30, message: '步骤2', detail: '' });
    state = reduceProgress(state, { stage: 50, message: '步骤3', detail: '' });
    expect(state.steps[0].status).toBe('done');
    expect(state.steps[1].status).toBe('done');
    expect(state.steps[2].status).toBe('doing');
  });
});

describe('markAllDone', () => {
  it('changes all doing steps to done', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 10, message: 'A', detail: '' });
    state = reduceProgress(state, { stage: 20, message: 'B', detail: '' });
    state = markAllDone(state);
    expect(state.steps.every((s) => s.status === 'done')).toBe(true);
  });
});

describe('markError', () => {
  it('marks the current doing step as error', () => {
    let state = createInitialState();
    state = reduceProgress(state, { stage: 50, message: '分析中', detail: '' });
    state = markError(state, '计算超时');
    expect(state.steps[0].status).toBe('error');
    expect(state.steps[0].detail).toBe('计算超时');
  });

  it('returns unchanged state when no doing step exists', () => {
    let state = createInitialState();
    state = markError(state, 'err');
    expect(state.steps).toHaveLength(0);
  });
});

describe('stepClass', () => {
  it('returns correct CSS class for each status', () => {
    expect(stepClass({ status: 'done' })).toBe('log-entry done');
    expect(stepClass({ status: 'doing' })).toBe('log-entry doing');
    expect(stepClass({ status: 'error' })).toBe('log-entry error');
    expect(stepClass({ status: 'pending' })).toBe('log-entry pending');
  });
});

describe('stepIconText', () => {
  it('returns ✓ for done', () => {
    expect(stepIconText({ status: 'done' }, 0)).toBe('✓');
  });
  it('returns ! for error', () => {
    expect(stepIconText({ status: 'error' }, 2)).toBe('!');
  });
  it('returns 1-based index for doing/pending', () => {
    expect(stepIconText({ status: 'doing' }, 0)).toBe('1');
    expect(stepIconText({ status: 'pending' }, 4)).toBe('5');
  });
});
