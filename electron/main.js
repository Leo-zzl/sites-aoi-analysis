const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');

const API_PORT = 8765;
let mainWindow = null;
let pythonProcess = null;

function isPortOpen(port) {
  return new Promise((resolve) => {
    const client = new net.Socket();
    client.setTimeout(1000);
    client.once('connect', () => {
      client.destroy();
      resolve(true);
    });
    client.once('error', () => resolve(false));
    client.once('timeout', () => {
      client.destroy();
      resolve(false);
    });
    client.connect(port, '127.0.0.1');
  });
}

async function waitForApi(maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    if (await isPortOpen(API_PORT)) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function resolvePythonCmd() {
  if (process.platform === 'win32') return 'python';
  // Prefer python3.11 when available (matches Homebrew setup on this machine)
  try {
    require('child_process').execSync('which python3.11', { stdio: 'ignore' });
    return 'python3.11';
  } catch {
    return 'python3';
  }
}

function startPythonBackend() {
  const isDev = !app.isPackaged;
  const pythonCmd = resolvePythonCmd();

  const args = ['-m', 'uvicorn', 'site_analysis.interfaces.api:app', '--port', String(API_PORT), '--host', '127.0.0.1'];

  // When running from source, we need to ensure src/ is on PYTHONPATH
  const env = { ...process.env };
  if (isDev) {
    const srcPath = path.resolve(__dirname, '..', 'src');
    env.PYTHONPATH = env.PYTHONPATH ? `${env.PYTHONPATH}${path.delimiter}${srcPath}` : srcPath;
  }

  pythonProcess = spawn(pythonCmd, args, {
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python] ${data.toString().trim()}`);
  });

  pythonProcess.on('exit', (code) => {
    console.log(`Python backend exited with code ${code}`);
    pythonProcess = null;
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 640,
    height: 900,
    minWidth: 560,
    minHeight: 720,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: 'default',
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  startPythonBackend();
  const ok = await waitForApi(40);
  if (!ok) {
    dialog.showErrorBox('启动失败', 'Python 分析引擎启动超时，请检查 Python 环境。');
    app.quit();
    return;
  }
  createWindow();
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('will-quit', () => {
  stopPythonBackend();
});

// IPC handlers
ipcMain.handle('api:upload', async (_event, fileType, filePath) => {
  const fs = require('fs');
  const FormData = require('form-data');
  const http = require('http');

  const form = new FormData();
  form.append('file_type', fileType);
  form.append('file', fs.createReadStream(filePath));

  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port: API_PORT,
        path: '/upload',
        method: 'POST',
        headers: form.getHeaders(),
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ error: data });
          }
        });
      }
    );
    req.on('error', reject);
    form.pipe(req);
  });
});

ipcMain.handle('api:validate', async (_event, params) => {
  return apiPost('/validate', params);
});

ipcMain.handle('api:analyze', async (_event, params) => {
  return apiPost('/analyze', params);
});

ipcMain.handle('api:jobStatus', async (_event, jobId) => {
  return apiGet(`/jobs/${jobId}`);
});

ipcMain.handle('dialog:openFile', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: '数据文件', extensions: ['xlsx', 'csv'] },
      { name: '所有文件', extensions: ['*'] },
    ],
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('dialog:saveFile', async (_event, defaultName) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: defaultName || `小区_AOI匹配_结果_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`,
    filters: [{ name: 'Excel 文件', extensions: ['xlsx'] }],
  });
  return result.canceled ? null : result.filePath;
});

function apiPost(apiPath, params) {
  const http = require('http');
  const postData = JSON.stringify(params);

  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port: API_PORT,
        path: apiPath,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData),
        },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ error: data });
          }
        });
      }
    );
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

function apiGet(apiPath) {
  const http = require('http');
  return new Promise((resolve, reject) => {
    http
      .get(`http://127.0.0.1:${API_PORT}${apiPath}`, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ error: data });
          }
        });
      })
      .on('error', reject);
  });
}
