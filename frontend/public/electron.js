const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess;

function startBackendServer() {
  return new Promise((resolve, reject) => {
    // プロジェクトルートを絶対パスで直指定
    const appRoot = "C:\\Users\\81701\\workspace\\lost_items_desktop";
    let backendPath, pythonPath, cwd;
    
    // 開発環境の判定を改善
    const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
    
    if (isDev) {
      // 開発環境
      backendPath = path.join(appRoot, 'app', 'main.py');
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      cwd = appRoot;
    } else {
      // 本番環境
      backendPath = path.join(process.resourcesPath, 'app', 'main.py');
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      cwd = process.resourcesPath;
      
      // 本番環境ではPythonパスをデフォルト値を使用
      if (process.platform === 'win32') {
        pythonPath = 'python';
      }
    }

    console.log('!!! THIS IS THE REAL electron.js !!!');

    console.log('=== Backend Server Startup ===');
    console.log('appRoot:', appRoot);
    console.log('Backend path:', backendPath);
    console.log('Python path:', pythonPath);
    console.log('Working directory:', cwd);
    console.log('Platform:', process.platform);
    console.log('process.cwd():', process.cwd());
    console.log('NODE_ENV:', process.env.NODE_ENV);
    console.log('process.resourcesPath:', process.resourcesPath);
    console.log('app.isPackaged:', app.isPackaged);
    // ファイルの存在確認
    if (!fs.existsSync(backendPath)) {
      console.error('Backend file not found:', backendPath);
      reject(new Error(`Backend file not found: ${backendPath}`));
      return;
    }

    console.log('Backend file found');

    // Pythonの存在確認
    const pythonCheck = spawn(pythonPath, ['--version'], { stdio: 'pipe' });
    pythonCheck.on('error', (error) => {
      console.error('Python not found:', error.message);
      reject(new Error(`Python not found: ${error.message}`));
    });

    pythonCheck.on('close', (code) => {
      if (code === 0) {
        console.log('Python found');
        startBackendProcess();
      } else {
        console.error('Python check failed with code:', code);
        reject(new Error(`Python check failed with code: ${code}`));
      }
    });

    function startBackendProcess() {
      console.log('Starting backend process...');
      
      // バックエンドサーバーの起動
      backendProcess = spawn(pythonPath, [backendPath], {
        cwd: cwd,
        stdio: 'pipe',
        env: { 
          ...process.env, 
          PYTHONPATH: cwd,
          PYTHONUNBUFFERED: '1'
        }
      });

      let serverStarted = false;

      backendProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log('Backend stdout:', output);
        
        if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
          console.log('Backend server started successfully');
          serverStarted = true;
          resolve();
        }
      });

      backendProcess.stderr.on('data', (data) => {
        const output = data.toString();
        console.log('Backend stderr:', output);
        
        // エラーでもサーバーが起動している可能性がある
        if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
          console.log('Backend server started (from stderr)');
          serverStarted = true;
          resolve();
        }
      });

      backendProcess.on('error', (error) => {
        console.error('Backend process error:', error);
        reject(error);
      });

      backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
        if (!serverStarted) {
          reject(new Error(`Backend process exited with code ${code}`));
        }
      });

      // タイムアウト設定
      setTimeout(() => {
        if (!serverStarted) {
          console.log('Backend server startup timeout, continuing...');
          resolve();
        }
      }, 10000); // 10秒待機
    }
  });
}

async function createWindow() {
  try {
    // バックエンドサーバーを起動
    console.log('Starting backend server...');
    await startBackendServer();
    console.log('Backend server started');
    
    // バックエンドサーバーの起動を確実に待つ
    console.log('Waiting for backend server to be ready...');
    await new Promise(resolve => setTimeout(resolve, 3000));
    console.log('Backend server ready');
  } catch (error) {
    console.error('Failed to start backend server:', error);
    // バックエンドが起動しなくてもフロントエンドは表示
  }

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'Lost Items Management System',
    show: false
  });

  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(process.resourcesPath, 'build', 'index.html').replace(/\\/g, '/')}`;
  
  console.log('Loading URL:', startUrl);
  mainWindow.loadURL(startUrl);

  // ウィンドウが準備できたら表示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    console.log('Main window shown');
  });

  if (isDev) {
    mainWindow.webContents.openDevTools();
  } else {
    // 本番環境でも開発者ツールを開く（デバッグ用）
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  // バックエンドプロセスを終了
  if (backendProcess) {
    console.log('Terminating backend process...');
    backendProcess.kill();
  }
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// アプリ終了時にバックエンドプロセスも終了
app.on('before-quit', () => {
  if (backendProcess) {
    console.log('Terminating backend process...');
    backendProcess.kill();
  }
}); 