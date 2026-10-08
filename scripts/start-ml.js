const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const mlDir = path.join(__dirname, '../ai-ml');
const venvPythonWin = path.join(mlDir, '.venv', 'Scripts', 'python.exe');
const venvPythonNix = path.join(mlDir, '.venv', 'bin', 'python');

let pythonCmd = 'python';
if (fs.existsSync(venvPythonWin)) {
  pythonCmd = venvPythonWin;
} else if (fs.existsSync(venvPythonNix)) {
  pythonCmd = venvPythonNix;
}

const child = spawn(pythonCmd, ['-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000'], {
  cwd: mlDir,
  stdio: 'inherit',
  shell: false,
});

child.on('error', (err) => {
  console.error('[ML Launcher] Failed to start Python process:', err.message);
  process.exit(1);
});

child.on('exit', (code) => process.exit(code || 0));
