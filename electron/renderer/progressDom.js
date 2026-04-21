/**
 * DOM helper functions for the progress log UI.
 * Extracted from app.js for testability.
 */

import { stepClass, stepIconText } from './progressState.js';

/**
 * Build a log entry DOM element from a progress step.
 * @param {{stage:number,message:string,detail:string,status:string}} step
 * @param {number} index
 * @returns {HTMLDivElement}
 */
export function createLogEntryElement(step, index) {
  const entry = document.createElement('div');
  entry.className = stepClass(step);

  const icon = document.createElement('div');
  icon.className = `log-icon ${step.status}`;
  icon.textContent = stepIconText(step, index);

  const body = document.createElement('div');
  body.className = 'log-body';

  const title = document.createElement('div');
  title.className = 'log-title';
  title.textContent = step.message;
  body.appendChild(title);

  if (step.detail) {
    const detail = document.createElement('div');
    detail.className = 'log-detail';
    detail.textContent = step.detail;
    body.appendChild(detail);
  }

  entry.appendChild(icon);
  entry.appendChild(body);
  return entry;
}

/**
 * Update an existing log entry DOM element to reflect a step's current state.
 * @param {HTMLDivElement} existing
 * @param {{stage:number,message:string,detail:string,status:string}} step
 * @param {number} index
 */
export function updateLogEntryElement(existing, step, index) {
  existing.className = stepClass(step);

  const icon = existing.querySelector('.log-icon');
  if (icon) {
    icon.className = `log-icon ${step.status}`;
    if (step.status === 'done') icon.textContent = '✓';
    else if (step.status === 'doing') icon.textContent = (index + 1).toString();
    else if (step.status === 'error') icon.textContent = '!';
  }

  let detailEl = existing.querySelector('.log-detail');
  if (detailEl) {
    detailEl.textContent = step.detail || '';
    detailEl.style.display = step.detail ? 'block' : 'none';
  } else if (step.detail) {
    const body = existing.querySelector('.log-body');
    if (body) {
      const d = document.createElement('div');
      d.className = 'log-detail';
      d.textContent = step.detail;
      d.style.display = 'block';
      body.appendChild(d);
    }
  }
}
