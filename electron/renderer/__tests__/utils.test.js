/* eslint-env browser */
import { describe, it, expect } from 'vitest';

// Pure utility extracted from app.js for testability
function defaultOutputName() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const ts = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `小区_AOI匹配_1000米限制_${ts}.xlsx`;
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
