const fs = require('fs');
const path = require('path');

const root = process.cwd();
const buildSubdir = path.join(root, 'dist', 'frontend_temp');
const dest = path.join(root, 'dist');

// If Vite placed files under dist/frontend_temp, move them into dist/
if (fs.existsSync(buildSubdir)) {
  fs.readdirSync(buildSubdir).forEach(f => {
    const s = path.join(buildSubdir, f);
    const d = path.join(dest, f);
    fs.renameSync(s, d);
    console.log(`Moved ${f} -> dist/`);
  });
  // remove now-empty frontend_temp dir
  try { fs.rmdirSync(buildSubdir); } catch(e) { /* ignore error */ }
}

// Copy remaining static assets from frontend_temp (script.css, style.css, assets/)
const src = path.join(root, 'frontend_temp');
const staticFiles = ['script.js', 'style.css'];
staticFiles.forEach(f => {
  const s = path.join(src, f);
  const d = path.join(dest, f);
  if (fs.existsSync(s)) {
    fs.copyFileSync(s, d);
    console.log(`Copied ${f} -> dist/`);
  }
});

const assetsDir = path.join(src, 'assets');
if (fs.existsSync(assetsDir)) {
  const targetAssets = path.join(dest, 'assets');
  fs.mkdirSync(targetAssets, { recursive: true });
  fs.readdirSync(assetsDir).forEach(f => {
    fs.copyFileSync(path.join(assetsDir, f), path.join(targetAssets, f));
  });
  console.log('Copied assets/ -> dist/assets/');
}

console.log('postbuild complete');
