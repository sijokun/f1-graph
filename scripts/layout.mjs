// Precompute the force layout offline so the page renders a settled graph.
// Each connected component is solved on its own, then components are packed
// around the largest one so disconnected subgraphs never overlap.
//
//   node scripts/layout.mjs                 # every graph in data/graphs/
//   node scripts/layout.mjs in.json out.json
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';

const GRAPH_DIR = new URL('../data/graphs/', import.meta.url);

if (process.argv[2]) {
  solveFile(process.argv[2], process.argv[3] ?? process.argv[2]);
} else {
  for (const f of readdirSync(GRAPH_DIR).sort()) {
    if (!f.endsWith('.json') || f === 'index.json') continue;
    const p = new URL(f, GRAPH_DIR).pathname;
    console.log(`--- ${f}`);
    solveFile(p, p);
  }
}

function solveFile(inPath, outPath) {
const data = JSON.parse(readFileSync(inPath, 'utf8'));
const N = data.nodes.length;
const tot = ys => ys.reduce((s, [, c]) => s + c, 0);
for (const l of data.links) l.w = tot(l.ys);
for (const n of data.nodes) n.races = tot(n.ys);
const maxW = Math.max(...data.links.map(l => l.w));
const sizes = data.nodes.map(n => 2 * (6 + Math.sqrt(n.races) * 0.95));

const deg = new Array(N).fill(0);
for (const l of data.links) { deg[l.s] += l.w; deg[l.t] += l.w; }

// ---- connected components (union-find) ----
const parent = [...Array(N).keys()];
const find = i => parent[i] === i ? i : (parent[i] = find(parent[i]));
for (const l of data.links) parent[find(l.s)] = find(l.t);
const compOf = new Map();
for (let i = 0; i < N; i++) {
  const root = find(i);
  if (!compOf.has(root)) compOf.set(root, []);
  compOf.get(root).push(i);
}
const components = [...compOf.values()].sort((a, b) => b.length - a.length);

const x = new Float64Array(N), y = new Float64Array(N);

// ---- solve one component in its own local frame ----
function solve(members) {
  const n = members.length;
  const lx = new Float64Array(n), ly = new Float64Array(n);
  const vx = new Float64Array(n), vy = new Float64Array(n);
  const li = new Map(members.map((g, k) => [g, k]));
  const links = data.links.filter(l => li.has(l.s));
  const order = [...Array(n).keys()].sort((a, b) => deg[members[b]] - deg[members[a]]);
  order.forEach((k, rank) => {
    const a = rank * 2.39996;
    const r = 30 + 26 * Math.sqrt(rank);
    lx[k] = Math.cos(a) * r;
    ly[k] = Math.sin(a) * r;
  });
  const ITER = n > 2 ? Math.min(3000, 400 + Math.round(4e8 / (n * n))) : 60;
  for (let t = 0; t < ITER; t++) {
    const alpha = Math.max(0.02, 1 - t / ITER);
    const repel = 1400, springK = 0.010, gravity = 0.008;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let dx = lx[i] - lx[j], dy = ly[i] - ly[j];
        let d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = (i % 2 ? 1 : -1); dy = 0.5; d2 = 1.25; }
        const d = Math.sqrt(d2);
        const f = repel / d2;
        vx[i] += (dx / d) * f; vy[i] += (dy / d) * f;
        vx[j] -= (dx / d) * f; vy[j] -= (dy / d) * f;
        const minD = (sizes[members[i]] + sizes[members[j]]) / 2 + 6;
        if (d < minD) {
          const push = (minD - d) * 0.35;
          vx[i] += (dx / d) * push; vy[i] += (dy / d) * push;
          vx[j] -= (dx / d) * push; vy[j] -= (dy / d) * push;
        }
      }
    }
    for (const l of links) {
      const a = li.get(l.s), b = li.get(l.t);
      // rest length is relative to the heaviest edge, so a graph whose counts
      // are small (podiums) spaces out like the teammate graph does
      const rest = 60 + 110 / (0.4 + (l.w / maxW) * 6.9);
      let dx = lx[b] - lx[a], dy = ly[b] - ly[a];
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = springK * (d - rest) * (0.5 + l.w / maxW);
      vx[a] += (dx / d) * f; vy[a] += (dy / d) * f;
      vx[b] -= (dx / d) * f; vy[b] -= (dy / d) * f;
    }
    for (let i = 0; i < n; i++) {
      vx[i] -= lx[i] * gravity;
      vy[i] -= ly[i] * gravity;
      lx[i] += vx[i] * alpha;
      ly[i] += vy[i] * alpha;
      vx[i] *= 0.5; vy[i] *= 0.5;
    }
  }
  // center on centroid, report bounding radius (including node size)
  let cx = 0, cy = 0;
  for (let i = 0; i < n; i++) { cx += lx[i]; cy += ly[i]; }
  cx /= n; cy /= n;
  let rad = 0;
  for (let i = 0; i < n; i++) {
    lx[i] -= cx; ly[i] -= cy;
    rad = Math.max(rad, Math.hypot(lx[i], ly[i]) + sizes[members[i]] / 2);
  }
  return { lx, ly, rad };
}

// ---- solve all, then pack small components around the main one ----
const solved = components.map(m => ({ members: m, ...solve(m) }));
const GAP = 60;
const placed = []; // {cx, cy, rad}
function overlaps(cx, cy, rad) {
  return placed.some(p => Math.hypot(cx - p.cx, cy - p.cy) < p.rad + rad + GAP);
}
solved.forEach((c, ci) => {
  let cx = 0, cy = 0;
  if (ci > 0) {
    // walk outward on a spiral until this component's circle fits
    const main = solved[0].rad;
    let a = ci * 0.9, r = main + c.rad + GAP;
    while (overlaps(cx = Math.cos(a) * r, cy = Math.sin(a) * r, c.rad)) {
      a += 0.35; r += 3;
    }
  }
  placed.push({ cx, cy, rad: c.rad });
  c.members.forEach((g, k) => { x[g] = cx + c.lx[k]; y[g] = cy + c.ly[k]; });
});

// ---- normalize into cosmos space (centered on 2048) ----
let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
for (let i = 0; i < N; i++) {
  minX = Math.min(minX, x[i]); maxX = Math.max(maxX, x[i]);
  minY = Math.min(minY, y[i]); maxY = Math.max(maxY, y[i]);
}
const cx0 = (minX + maxX) / 2, cy0 = (minY + maxY) / 2;
data.pos = [];
for (let i = 0; i < N; i++) data.pos.push(+(2048 + x[i] - cx0).toFixed(1), +(2048 + y[i] - cy0).toFixed(1));

for (const l of data.links) delete l.w;
for (const n of data.nodes) delete n.races;
writeFileSync(outPath, JSON.stringify(data));
console.log(`components: ${components.slice(0, 8).map(c => c.length).join(', ')}${components.length > 8 ? `, … (${components.length} total)` : ''}`);
console.log(`layout done: extent ${(maxX - minX).toFixed(0)}×${(maxY - minY).toFixed(0)}`);
}
