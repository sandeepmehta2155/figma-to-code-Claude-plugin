#!/usr/bin/env node
// Pixel diff of the Figma frame render vs a screenshot of the build, then the areas that differ most.
// Usage: node visual_diff.mjs <figma.png> <build.png> <diff.png> [threshold=0.1] [--scale=N]
//        node visual_diff.mjs --frame <figma.png> [--scale=N]    # the frame's size inside its render
//        node visual_diff.mjs self-test
// --scale is the Figma render's scale (LLM Export bundles: 2). Deps install into this folder on
// first run (not into the user's project).
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import assert from 'node:assert/strict';

const dir = dirname(fileURLToPath(import.meta.url));
const usage = 'usage: node visual_diff.mjs <figma.png> <build.png> <diff.png> [threshold] [--scale=N]\n' +
  '       node visual_diff.mjs --frame <figma.png> [--scale=N]\n       node visual_diff.mjs self-test';
let args;
try {
  args = parseArgs({ allowPositionals: true, options: { scale: { type: 'string', default: '1' }, frame: { type: 'boolean' } } });
} catch (e) {
  console.error(`${e.message}\n${usage}`);
  process.exit(1);
}
const pos = args.positionals, scale = Number(args.values.scale);
if (!pos.length || !(scale > 0)) {
  console.error(usage);
  process.exit(1);
}

if (!existsSync(join(dir, 'node_modules', 'pixelmatch'))) {
  execFileSync('npm', ['install', '--prefix', dir, '--no-audit', '--no-fund', '--silent'], { stdio: 'inherit', shell: process.platform === 'win32' });
}
const { PNG } = createRequire(join(dir, 'package.json'))('pngjs');
const { default: pixelmatch } = await import(pathToFileURL(join(dir, 'node_modules', 'pixelmatch', 'index.js')));
const read = (path) => PNG.sync.read(readFileSync(path));
const crop = (png, x, y, width, height) => {
  const out = new PNG({ width, height });
  PNG.bitblt(png, out, x, y, width, height, 0, 0);
  return out;
};

// A frame with a drop shadow renders larger than itself: the shadow is a translucent margin
// and the frame is the box of fully opaque pixels.
// ponytail: assumes the frame has an opaque fill (screens do); a see-through frame needs its size from Figma.
function frameBox(png) {
  let x0 = png.width, y0 = png.height, x1 = -1, y1 = -1;
  for (let y = 0; y < png.height; y++) {
    for (let x = 0; x < png.width; x++) {
      if (png.data[(y * png.width + x) * 4 + 3] !== 255) continue;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      y1 = y;
    }
  }
  return x1 < 0 ? null : { x: x0, y: y0, width: x1 - x0 + 1, height: y1 - y0 + 1 };
}

// Line the render up with the build: crop a drop shadow off the render, and compare only the height both
// cover when the page runs past or ends above the frame's bottom. Never resize: resizing hides exactly the
// drift we're looking for.
function align(a, b) {
  const notes = [], f = frameBox(a);
  const shadow = f && (f.width < a.width || f.height < a.height) ? f : null;
  if (shadow && b.width === f.width) {
    a = crop(a, f.x, f.y, f.width, f.height);
    notes.push(`cropped the Figma render to its frame (${f.width}x${f.height} at ${f.x},${f.y}); the rest was drop shadow`);
  } else if (shadow && b.width === a.width) {
    notes.push(`warning: the frame is ${f.width}x${f.height} at ${f.x},${f.y} inside the render (the rest is drop shadow), ` +
      "but the build was shot at the render's width, so this diff is shifted: reshoot at the frame's size");
  }
  if (b.width === a.width && b.height > a.height) {
    b = crop(b, 0, 0, a.width, a.height);
    notes.push(`clipped the build to the Figma image's height (${a.height}px); the page continues below it`);
  } else if (b.width === a.width && b.height < a.height) {
    notes.push(`the page ends ${a.height - b.height}px above the frame's bottom (or the shot wasn't full-page): compared the top ${b.height}px only`);
    a = crop(a, 0, 0, a.width, b.height);
  }
  return { a, b, notes, frame: shadow || a };
}

// Mean color of each 8 CSS px block in both images (averaging washes out anti-aliasing and font
// rasterization); a block counts as changed when a channel moves more than 40. Reported per 160 CSS px cell.
// ponytail: tuned on dark dashboards; lower the 40 if light pages under-report. Edge strips under one block are skipped.
function areas(a, b, s) {
  const B = Math.max(1, Math.round(8 * s)), C = 20 * B, cols = Math.ceil(a.width / C), cells = new Map();
  const mean = (png, x0, y0) => {
    const m = [0, 0, 0];
    for (let y = y0; y < y0 + B; y++) {
      for (let x = x0; x < x0 + B; x++) {
        const i = (y * png.width + x) * 4, alpha = png.data[i + 3] / 255;
        for (let k = 0; k < 3; k++) m[k] += png.data[i + k] * alpha + 255 * (1 - alpha); // onto white
      }
    }
    return m.map((v) => v / (B * B));
  };
  for (let y = 0; y + B <= a.height; y += B) {
    for (let x = 0; x + B <= a.width; x += B) {
      const m = mean(a, x, y), n = mean(b, x, y), key = Math.floor(y / C) * cols + Math.floor(x / C);
      const cell = cells.get(key) || { x: Math.round(((key % cols) * C) / s), y: Math.round((Math.floor(key / cols) * C) / s), changed: 0, blocks: 0 };
      cell.blocks++;
      if (Math.max(...m.map((v, k) => Math.abs(v - n[k]))) > 40) cell.changed++;
      cells.set(key, cell);
    }
  }
  return [...cells.values()].map((c) => ({ x: c.x, y: c.y, pct: (100 * c.changed) / c.blocks }));
}

function selfTest() {
  const W = 640;
  const square = (x0, y0, w = W, h = W) => {
    const png = new PNG({ width: w, height: h });
    png.data.fill(255);
    for (let y = y0; y < y0 + 40; y++) for (let x = x0; x < x0 + 40; x++) png.data.fill(0, (y * w + x) * 4, (y * w + x) * 4 + 3);
    return png;
  };
  const a = square(40, 40), b = square(200, 520);
  const top = (s) => areas(a, b, s).sort((p, q) => q.pct - p.pct).slice(0, 2).map((c) => `${c.x},${c.y}`).sort();
  assert.deepEqual(top(1), ['0,0', '160,480']);
  assert.deepEqual(top(2), ['0,0', '0,160']); // CSS px at scale 2
  assert.ok(areas(a, a, 2).every((c) => c.pct === 0));
  const shadowed = new PNG({ width: W + 28, height: W + 28 });
  shadowed.data.fill(128); // a translucent margin, like a drop shadow
  PNG.bitblt(a, shadowed, 0, 0, W, W, 14, 2);
  assert.deepEqual(frameBox(shadowed), { x: 14, y: 2, width: W, height: W });
  let r = align(shadowed, a);
  assert.ok(r.a.width === W && r.a.height === W && /^cropped/.test(r.notes[0]));
  r = align(shadowed, square(40, 40, W + 28, W + 28)); // build shot at the render's size
  assert.ok(/^warning/.test(r.notes[0]));
  r = align(a, square(40, 40, W, W + 100)); // full-page build taller than the frame
  assert.ok(r.b.height === W && /^clipped/.test(r.notes[0]));
  r = align(a, square(40, 40, W, W - 100)); // page shorter than the frame
  assert.ok(r.a.height === W - 100 && /^the page ends 100px/.test(r.notes[0]));
  console.log('ok');
}

if (pos[0] === 'self-test') {
  selfTest();
  process.exit(0);
}

if (args.values.frame) {
  const png = read(pos[0]);
  const f = frameBox(png) || { x: 0, y: 0, width: png.width, height: png.height };
  const css = `${f.width / scale}x${f.height / scale} CSS px at scale ${scale}`;
  console.log(f.width === png.width && f.height === png.height
    ? `frame: the whole render, ${css}`
    : `frame: ${f.width}x${f.height} px at ${f.x},${f.y} inside a ${png.width}x${png.height} render = ${css} (the rest is drop shadow)`);
  process.exit(0);
}

const [figmaPath, buildPath, diffPath, threshold = '0.1'] = pos;
if (!diffPath || pos.length > 4 || !(Number(threshold) >= 0 && Number(threshold) < 1)) {
  console.error(usage);
  process.exit(1);
}
const { a, b, notes, frame } = align(read(figmaPath), read(buildPath));
if (a.width !== b.width || a.height !== b.height) {
  const css = `${frame.width / scale}x${frame.height / scale}`;
  console.error(`size mismatch: figma frame ${frame.width}x${frame.height} px = ${css} CSS px at --scale=${scale}, build ${b.width}x${b.height} px. ` +
    `Screenshot the build at the frame's CSS width with device scale ${scale}.`);
  process.exit(2);
}

const diff = new PNG({ width: a.width, height: a.height });
const bad = pixelmatch(a.data, b.data, diff.data, a.width, a.height, { threshold: Number(threshold) });
writeFileSync(diffPath, PNG.sync.write(diff));
const pct = ((bad / (a.width * a.height)) * 100).toFixed(2);
console.log(`mismatch: ${bad} px (${pct}%) of ${a.width}x${a.height} -> ${diffPath}`);
for (const note of notes) console.log(note);

const cells = areas(a, b, scale);
const median = cells.map((c) => c.pct).sort((p, q) => p - q)[cells.length >> 1] ?? 0;
const top = cells.filter((c) => c.pct > 0).sort((p, q) => q.pct - p.pct).slice(0, 8);
console.log(top.length
  ? `areas that differ most (160px cells at x,y in CSS px, % of 8px blocks changed; median cell ${median.toFixed(1)}% = noise floor):\n` +
    top.map((c) => `  x=${c.x} y=${c.y}  ${c.pct.toFixed(1)}%`).join('\n')
  : bad
    ? 'no 8px block moved more than 40 per channel: the mismatch is thin or faint (1px shifts, anti-aliasing, slight color changes), so open the diff image'
    : 'no area differs');
