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
  progressFill: document.getElementById('progress-fill'),
  progressText: document.getElementById('progress-text'),
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
  if (!els.outputPath.value) {
    showError('提示', '请先设置输出文件路径');
    return;
  }

  setAnalyzing(true);
  setProgress(5, '准备分析...');

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

  const res = await window.electronAPI.analyze(params);
  if (res.error) {
    setAnalyzing(false);
    setProgress(0, '');
    showError('分析失败', res.error);
    return;
  }

  state.jobId = res.job_id;
  connectProgress(res.job_id);
});

function setProgress(percent, text) {
  els.progressFill.style.width = `${percent}%`;
  els.progressText.textContent = text || '';
}

function setAnalyzing(active) {
  els.analyzeBtn.disabled = active;
  els.analyzeBtn.textContent = active ? '分析中...' : '开始分析';
  els.validateBtn.disabled = active;
  els.aoiBtn.disabled = active;
  els.siteBtn.disabled = active;
  [els.aoiScene, els.aoiBoundary, els.siteNameCol, els.siteLon, els.siteLat, els.siteFreq, els.siteCover].forEach((el) => {
    el.disabled = active;
  });
}

function connectProgress(jobId) {
  const es = new EventSource(`${API_BASE}/progress/${jobId}`);

  es.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    setProgress(data.stage, data.message + (data.detail ? ` (${data.detail})` : ''));
  });

  es.addEventListener('complete', async (e) => {
    es.close();
    const data = JSON.parse(e.data);
    setAnalyzing(false);

    if (data.error) {
      setProgress(0, '');
      showError('分析失败', data.error + '\n' + (data.traceback || ''));
      return;
    }

    setProgress(100, '分析完成');

    const status = await window.electronAPI.jobStatus(jobId);
    if (status.summary) {
      const s = status.summary;
      els.validateMsg.innerHTML =
        `分析完成！总站点数：${s.total_sites}  |  AOI已匹配：${s.aoi_matched}  |  室内站：${s.indoor_sites}  |  室外站：${s.outdoor_sites}  |  1000米内找到室外站：${s.indoor_with_outdoor}`;
      els.validateMsg.className = 'validate-msg success';
    } else {
      els.validateMsg.textContent = '分析完成';
      els.validateMsg.className = 'validate-msg success';
    }

    const dl = await window.electronAPI.download(jobId);
    if (!dl.canceled) {
      setProgress(100, `结果已保存至：${dl.filePath}`);
    }
  });

  es.addEventListener('error', () => {
    es.close();
    setAnalyzing(false);
  });
}

function showError(title, message) {
  // Simple alert for now; Electron could expose a nicer dialog if needed
  alert(`${title}\n${message}`);
}
