const { contextBridge } = require('electron');

// セキュリティのため、レンダラープロセスに公開するAPIを制限
contextBridge.exposeInMainWorld('electronAPI', {
  // 必要に応じてAPIを追加
}); 