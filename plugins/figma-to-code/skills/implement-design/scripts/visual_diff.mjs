#!/usr/bin/env node
// Pixel diff of the Figma frame render vs a screenshot of the build.
// Usage: node visual_diff.mjs <figma.png> <build.png> <diff.png> [threshold=0.1]
// Deps install into this folder on first run (not into the user's project).
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const dir = dirname(fileURLToPath(import.meta.url));
const [figmaPath, buildPath, diffPath, threshold = '0.1'] = process.argv.slice(2);
if (!diffPath) {
  console.error('usage: node visual_diff.mjs <figma.png> <build.png> <diff.png> [threshold]');
  process.exit(1);
}

if (!existsSync(join(dir, 'node_modules', 'pixelmatch'))) {
  execFileSync('npm', ['install', '--prefix', dir, '--no-audit', '--no-fund', '--silent'], { stdio: 'inherit', shell: process.platform === 'win32' });
}
const { PNG } = createRequire(join(dir, 'package.json'))('pngjs');
const { default: pixelmatch } = await import(pathToFileURL(join(dir, 'node_modules', 'pixelmatch', 'index.js')));

const a = PNG.sync.read(readFileSync(figmaPath));
const b = PNG.sync.read(readFileSync(buildPath));
// Never resize to make them fit: resizing hides exactly the drift we're looking for.
if (a.width !== b.width || a.height !== b.height) {
  console.error(`size mismatch: figma ${a.width}x${a.height}, build ${b.width}x${b.height}. ` +
    'Screenshot the build at the frame size (viewport = frame width, deviceScaleFactor 1, clip to frame height).');
  process.exit(2);
}

const diff = new PNG({ width: a.width, height: a.height });
const bad = pixelmatch(a.data, b.data, diff.data, a.width, a.height, { threshold: Number(threshold) });
writeFileSync(diffPath, PNG.sync.write(diff));
const pct = ((bad / (a.width * a.height)) * 100).toFixed(2);
console.log(`mismatch: ${bad} px (${pct}%) of ${a.width}x${a.height} -> ${diffPath}`);
