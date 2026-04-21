import { describe, it, expect, beforeEach } from 'vitest';
import { createLogEntryElement, updateLogEntryElement } from '../progressDom.js';

describe('createLogEntryElement', () => {
  it('renders done step with checkmark icon', () => {
    const el = createLogEntryElement(
      { stage: 10, message: '加载完成', detail: '', status: 'done' },
      0
    );
    expect(el.classList.contains('log-entry')).toBe(true);
    expect(el.classList.contains('done')).toBe(true);
    const icon = el.querySelector('.log-icon');
    expect(icon.textContent).toBe('✓');
    expect(icon.classList.contains('done')).toBe(true);
  });

  it('renders doing step with 1-based index icon', () => {
    const el = createLogEntryElement(
      { stage: 50, message: '分析中', detail: '处理中', status: 'doing' },
      2
    );
    expect(el.classList.contains('doing')).toBe(true);
    const icon = el.querySelector('.log-icon');
    expect(icon.textContent).toBe('3');
    const detail = el.querySelector('.log-detail');
    expect(detail).not.toBeNull();
    expect(detail.textContent).toBe('处理中');
  });

  it('renders error step with exclamation icon', () => {
    const el = createLogEntryElement(
      { stage: 50, message: '出错', detail: '超时', status: 'error' },
      0
    );
    expect(el.classList.contains('error')).toBe(true);
    const icon = el.querySelector('.log-icon');
    expect(icon.textContent).toBe('!');
  });

  it('does not render detail element when detail is empty', () => {
    const el = createLogEntryElement(
      { stage: 10, message: '无详情', detail: '', status: 'pending' },
      0
    );
    const detail = el.querySelector('.log-detail');
    expect(detail).toBeNull();
  });
});

describe('updateLogEntryElement', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  it('updates class and icon when status changes to done', () => {
    const step = { stage: 10, message: '步骤1', detail: '', status: 'doing' };
    const el = createLogEntryElement(step, 0);
    container.appendChild(el);

    updateLogEntryElement(el, { ...step, status: 'done' }, 0);
    expect(el.classList.contains('done')).toBe(true);
    expect(el.querySelector('.log-icon').textContent).toBe('✓');
  });

  it('adds detail element when detail appears later', () => {
    const step = { stage: 10, message: '步骤1', detail: '', status: 'doing' };
    const el = createLogEntryElement(step, 0);
    container.appendChild(el);

    updateLogEntryElement(el, { ...step, detail: '已识别 5 个 AOI' }, 0);
    const detail = el.querySelector('.log-detail');
    expect(detail).not.toBeNull();
    expect(detail.textContent).toBe('已识别 5 个 AOI');
    expect(detail.style.display).toBe('block');
  });

  it('hides detail element when detail is cleared', () => {
    const step = { stage: 10, message: '步骤1', detail: '旧详情', status: 'doing' };
    const el = createLogEntryElement(step, 0);
    container.appendChild(el);

    updateLogEntryElement(el, { ...step, detail: '' }, 0);
    const detail = el.querySelector('.log-detail');
    expect(detail.style.display).toBe('none');
  });
});
