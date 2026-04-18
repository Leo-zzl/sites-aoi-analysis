const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  uploadFile: (fileType, filePath) => ipcRenderer.invoke('api:upload', fileType, filePath),
  validate: (params) => ipcRenderer.invoke('api:validate', params),
  analyze: (params) => ipcRenderer.invoke('api:analyze', params),
  jobStatus: (jobId) => ipcRenderer.invoke('api:jobStatus', jobId),
  openFile: () => ipcRenderer.invoke('dialog:openFile'),
  saveFile: (defaultName) => ipcRenderer.invoke('dialog:saveFile', defaultName),
});
