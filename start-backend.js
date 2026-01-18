const { spawn } = require('child_process');
const path = require('path');

const backendDir = path.join(__dirname, 'backend');
const venvPython = path.join(backendDir, 'venv', 'Scripts', 'python.exe');
const serverScript = path.join(backendDir, 'server.py');

console.log('Starting backend server...');
console.log('Python:', venvPython);
console.log('Server:', serverScript);

const proc = spawn(venvPython, [serverScript], {
  cwd: backendDir,
  stdio: 'inherit',
  env: { ...process.env }
});

proc.on('error', (err) => {
  console.error('Failed to start backend:', err);
});

proc.on('close', (code) => {
  console.log('Backend exited with code:', code);
});
