/* eslint-env browser */

const API_BASE = 'http://127.0.0.1:8765';

let state = {
  aoiSessionId: null,
  siteSessionId: null,
  aoiColumns: [],
  siteColumns: [],
  valid: false,
  jobId: null,
};

let progressState = {
  steps: [],
  isRunning: false,
};

const els = {
  aoiBtn: document.getElementById('aoi-btn'),
  aoiName: document.getElementById('aoi-name'),
  aoiScene: document.getElementById('aoi-scene'),
  aoiBoundary: document.getElementById('aoi-boundary'),

  siteBtn: document.getElementById('site-btn'),
  siteNameLabel: document.getElementById('site-name'),
  siteNameCol: document.getElementById('site-name-col'),
  siteLon: document.getElementById('site-lon'),
  siteLat: document.getElementById('site-lat'),
  siteFreq: document.getElementById('site-freq'),
  siteCover: document.getElementById('site-cover'),

  validateBtn: document.getElementById('validate-btn'),
  validateMsg: document.getElementById('validate-msg'),

  outputPath: document.getElementById('output-path'),
  browseBtn: document.getElementById('browse-btn'),

  analyzeBtn: document.getElementById('analyze-btn'),
  stopBtn: document.getElementById('stop-btn'),
  progressBar: document.getElementById('progress-bar'),
  progressFill: document.getElementById('progress-fill'),
  progressStage: document.getElementById('progress-stage'),
  progressDots: document.getElementById('progress-dots'),
  progressDetail: document.getElementById('progress-detail'),
  progressLog: document.getElementById('progress-log'),
  summaryCard: document.getElementById('summary-card'),
  sumTotal: document.getElementById('sum-total'),
  sumAoi: document.getElementById('sum-aoi'),
  sumIndoor: document.getElementById('sum-indoor'),
};

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

function resetValidation() {
  state.valid = false;
  els.validateMsg.textContent = '请先点击【校验数据】检查文件格式';
  els.validateMsg.className = 'validate-msg';
  els.analyzeBtn.disabled = true;
}

async function pickFile(type) {
  const filePath = await window.electronAPI.openFile();
  if (!filePath) return;

  const res = await window.electronAPI.uploadFile(type, filePath);
  if (res.error) {
    showError('上传失败', res.error);
    return;
  }

  if (type === 'aoi') {
    state.aoiSessionId = res.session_id;
    state.aoiColumns = res.columns || [];
    els.aoiName.textContent = res.file_name;
    setSelectOptions(els.aoiScene, state.aoiColumns, res.mapping.scene_col);
    setSelectOptions(els.aoiBoundary, state.aoiColumns, res.mapping.boundary_col);
  } else {
    state.siteSessionId = res.session_id;
    state.siteColumns = res.columns || [];
    els.siteNameLabel.textContent = res.file_name;
    setSelectOptions(els.siteNameCol, state.siteColumns, res.mapping.name_col);
    setSelectOptions(els.siteLon, state.siteColumns, res.mapping.lon_col);
    setSelectOptions(els.siteLat, state.siteColumns, res.mapping.lat_col);
    setSelectOptions(els.siteFreq, state.siteColumns, res.mapping.freq_col);
    setSelectOptions(els.siteCover, state.siteColumns, res.mapping.coverage_type_col);
  }
  resetValidation();
}

els.aoiBtn.addEventListener('click', () => pickFile('aoi'));
els.siteBtn.addEventListener('click', () => pickFile('site'));

[els.aoiScene, els.aoiBoundary, els.siteNameCol, els.siteLon, els.siteLat, els.siteFreq, els.siteCover].forEach((el) => {
  el.addEventListener('change', resetValidation);
});

els.validateBtn.addEventListener('click', async () => {
  if (!state.aoiSessionId || !state.siteSessionId) {
    els.validateMsg.textContent = '请先选择 AOI 文件和站点文件';
    els.validateMsg.className = 'validate-msg error';
    return;
  }

  els.validateMsg.textContent = '正在校验数据格式与字段映射...';
  els.validateMsg.className = 'validate-msg';

  const params = {
    aoi_session_id: state.aoiSessionId,
    site_session_id: state.siteSessionId,
    scene_col: els.aoiScene.value,
    boundary_col: els.aoiBoundary.value,
    name_col: els.siteNameCol.value,
    lon_col: els.siteLon.value,
    lat_col: els.siteLat.value,
    freq_col: els.siteFreq.value,
    coverage_type_col: els.siteCover.value,
  };

  const res = await window.electronAPI.validate(params);
  if (res.error) {
    els.validateMsg.textContent = '校验异常：' + res.error;
    els.validateMsg.className = 'validate-msg error';
    return;
  }

  if (res.valid) {
    state.valid = true;
    els.validateMsg.textContent = '校验通过，可以点击【开始分析】';
    els.validateMsg.className = 'validate-msg success';
    els.analyzeBtn.disabled = false;
  } else {
    state.valid = false;
    els.validateMsg.textContent = '校验失败，请检查字段映射与数据格式';
    els.validateMsg.className = 'validate-msg error';
    els.analyzeBtn.disabled = true;
    showError('校验失败', (res.errors || []).join('\n'));
  }
});

els.browseBtn.addEventListener('click', async () => {
  const filePath = await window.electronAPI.saveFile(els.outputPath.value || defaultOutputName());
  if (filePath) {
    els.outputPath.value = filePath;
  }
});

els.outputPath.value = defaultOutputName();

els.analyzeBtn.addEventListener('click', async () => {
  if (!state.valid) return;

  let outPath = els.outputPath.value.trim();
  if (!outPath) {
    const chosen = await window.electronAPI.saveFile(defaultOutputName());
    if (!chosen) return;
    outPath = chosen;
    els.outputPath.value = outPath;
  }

  resetProgress();
  setAnalyzing(true);
  updateProgress({ stage: 5, message: '准备分析...', detail: '' });

  const params = {
    aoi_session_id: state.aoiSessionId,
    site_session_id: state.siteSessionId,
    output_path: outPath,
    scene_col: els.aoiScene.value,
    boundary_col: els.aoiBoundary.value,
    name_col: els.siteNameCol.value,
    lon_col: els.siteLon.value,
    lat_col: els.siteLat.value,
    freq_col: els.siteFreq.value,
    coverage_type_col: els.siteCover.value,
  };

  const res = await window.electronAPI.analyze(params);
  if (res.error) {
    setAnalyzing(false);
    resetProgress();
    showError('分析失败', res.error);
    return;
  }

  state.jobId = res.job_id;
  connectProgress(res.job_id);
});

els.stopBtn.addEventListener('click', async () => {
  if (!state.jobId) return;
  updateProgress({ stage: parseInt(els.progressFill.style.width) || 0, message: '正在取消...', detail: '' });
  try {
    await fetch(`${API_BASE}/cancel/${state.jobId}`, { method: 'POST' });
  } catch (e) {
    console.error('Cancel failed', e);
  }
});

import { createInitialState, reduceProgress, markAllDone, markError, stepClass, stepIconText } from './progressState.js';

// Progress state machine
function resetProgress() {
  progressState = createInitialState();
  els.progressFill.style.width = '0%';
  els.progressBar.classList.remove('active');
  els.progressStage.textContent = '';
  els.progressDetail.textContent = '';
  els.progressLog.innerHTML = '';
  els.progressDots.classList.add('hidden');
  els.summaryCard.style.display = 'none';
}

function updateProgress(data) {
  const { stage, message, detail, heartbeat } = data;

  // Update bar (always, so width stays current)
  els.progressFill.style.width = `${stage}%`;

  // Heartbeat: keep animation alive but do NOT touch the log
  if (heartbeat) {
    return;
  }

  // Update current stage text
  if (message) {
    els.progressStage.textContent = message;
  }
  if (detail !== undefined) {
    els.progressDetail.textContent = detail;
  }

  const prevSteps = progressState.steps;
  progressState = reduceProgress(progressState, data);

  // Determine what changed so we only touch the DOM when necessary
  const existingIndex = prevSteps.findIndex((s) => s.message === message);
  if (existingIndex >= 0) {
    const step = progressState.steps[existingIndex];
    const detailChanged = prevSteps[existingIndex].detail !== detail;
    if (detailChanged) {
      updateLogEntry(existingIndex, step);
    }
  } else {
    // New step arrived – mark previous doing as done, append new entry
    prevSteps.forEach((s, idx) => {
      if (s.status === 'doing') {
        updateLogEntry(idx, progressState.steps[idx]);
      }
    });
    appendLogEntry(progressState.steps[progressState.steps.length - 1], progressState.steps.length - 1);
  }
}

function appendLogEntry(step, index) {
  const entry = createLogEntryElement(step, index);
  els.progressLog.appendChild(entry);
  els.progressLog.scrollTop = els.progressLog.scrollHeight;
}

function updateLogEntry(index, step) {
  const existing = els.progressLog.children[index];
  if (!existing) {
    appendLogEntry(step, index);
    return;
  }
  // Update class
  existing.className = `log-entry ${step.status}`;
  // Update icon
  const icon = existing.querySelector('.log-icon');
  if (icon) {
    icon.className = `log-icon ${step.status}`;
    if (step.status === 'done') icon.textContent = '✓';
    else if (step.status === 'doing') icon.textContent = (index + 1).toString();
    else if (step.status === 'error') icon.textContent = '!';
  }
  // Update detail
  const detailEl = existing.querySelector('.log-detail');
  if (detailEl) {
    detailEl.textContent = step.detail || '';
    detailEl.style.display = step.detail ? 'block' : 'none';
  } else if (step.detail) {
    const body = existing.querySelector('.log-body');
    if (body) {
      const d = document.createElement('div');
      d.className = 'log-detail';
      d.textContent = step.detail;
      body.appendChild(d);
    }
  }
}

function createLogEntryElement(step, index) {
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

function setAnalyzing(active) {
  progressState.isRunning = active;
  els.analyzeBtn.disabled = active;
  els.analyzeBtn.textContent = active ? '分析中...' : '开始分析';
  els.stopBtn.style.display = active ? 'inline-flex' : 'none';
  els.validateBtn.disabled = active;
  els.aoiBtn.disabled = active;
  els.siteBtn.disabled = active;
  els.browseBtn.disabled = active;
  [els.aoiScene, els.aoiBoundary, els.siteNameCol, els.siteLon, els.siteLat, els.siteFreq, els.siteCover].forEach((el) => {
    el.disabled = active;
  });

  if (active) {
    els.progressBar.classList.add('active');
    els.progressDots.classList.remove('hidden');
  } else {
    els.progressBar.classList.remove('active');
    els.progressDots.classList.add('hidden');
  }
}

function renderSummaryCard(summary) {
  if (!summary) return;
  els.sumTotal.textContent = summary.total_sites || 0;
  els.sumAoi.textContent = summary.aoi_matched || 0;
  els.sumIndoor.textContent = summary.indoor_with_outdoor || 0;
  els.summaryCard.style.display = 'block';
}

function connectProgress(jobId) {
  const es = new EventSource(`${API_BASE}/progress/${jobId}`);

  es.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    updateProgress(data);
  });

  es.addEventListener('complete', async (e) => {
    es.close();
    const data = JSON.parse(e.data);
    setAnalyzing(false);

    if (data.cancelled) {
      resetProgress();
      els.validateMsg.textContent = '取消成功';
      els.validateMsg.className = 'validate-msg error';
      return;
    }

    if (data.error) {
      progressState = markError(progressState, data.error);
      const idx = progressState.steps.findIndex((s) => s.status === 'error');
      if (idx >= 0) updateLogEntry(idx, progressState.steps[idx]);
      showError('分析失败', data.error + '\n' + (data.traceback || ''));
      return;
    }

    // Mark all as done
    progressState = markAllDone(progressState);
    progressState.steps.forEach((s, idx) => {
      if (s.status === 'done') updateLogEntry(idx, s);
    });

    const status = await window.electronAPI.jobStatus(jobId);
    if (status.summary) {
      renderSummaryCard(status.summary);
      const s = status.summary;
      els.validateMsg.innerHTML =
        `分析完成！总站点数：${s.total_sites}  |  AOI已匹配：${s.aoi_matched}  |  室内站：${s.indoor_sites}  |  室外站：${s.outdoor_sites}  |  1000米内找到室外站：${s.indoor_with_outdoor}`;
      els.validateMsg.className = 'validate-msg success';
    } else {
      els.validateMsg.textContent = '分析完成';
      els.validateMsg.className = 'validate-msg success';
    }
  });

  es.addEventListener('error', () => {
    es.close();
    setAnalyzing(false);
  });
}

function showError(title, message) {
  alert(`${title}\n${message}`);
}

// Initial state: hide progress indicators until analysis starts
resetProgress();
