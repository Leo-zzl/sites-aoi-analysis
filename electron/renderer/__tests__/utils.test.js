/* eslint-env browser */
import { describe, it, expect } from 'vitest';

// Pure utility extracted from app.js for testability
function defaultOutputName() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const ts = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `小区_AOI匹配_1000米限制_${ts}.xlsx`;
}

function setSelectOptions(selectEl, columns, selectedValue) {
  selectEl.innerHTML = '';
  const empty = document.createElement('option');
  empty.value = '';
  empty.textContent = '请选择';
  selectEl.appendChild(empty);
  columns.forEach((col) => {
    const opt = document.createElement('option');
    opt.value = col;
    opt.textContent = col;
    selectEl.appendChild(opt);
  });
  if (selectedValue) {
    selectEl.value = selectedValue;
  }
}

describe('defaultOutputName', () => {
  it('returns a string containing the expected prefix and extension', () => {
    const name = defaultOutputName();
    expect(name).toContain('小区_AOI匹配_1000米限制_');
    expect(name).toContain('.xlsx');
  });

  it('includes a timestamp in the filename', () => {
    const name = defaultOutputName();
    const match = name.match(/_(\d{8}_\d{6})\.xlsx$/);
    expect(match).not.toBeNull();
    expect(match[1].length).toBe(15); // YYYYMMDD_HHMMSS
  });
});

describe('setSelectOptions', () => {
  it('clears existing options and adds placeholder', () => {
    const sel = document.createElement('select');
    sel.innerHTML = '<option>old</option>';
    setSelectOptions(sel, [], '');
    expect(sel.options.length).toBe(1);
    expect(sel.options[0].textContent).toBe('请选择');
    expect(sel.options[0].value).toBe('');
  });

  it('populates options from columns array', () => {
    const sel = document.createElement('select');
    setSelectOptions(sel, ['A', 'B', 'C'], '');
    expect(sel.options.length).toBe(4); // placeholder + 3
    expect(sel.options[1].value).toBe('A');
    expect(sel.options[2].value).toBe('B');
    expect(sel.options[3].value).toBe('C');
  });

  it('sets selected value when provided', () => {
    const sel = document.createElement('select');
    setSelectOptions(sel, ['A', 'B'], 'B');
    expect(sel.value).toBe('B');
  });
});
