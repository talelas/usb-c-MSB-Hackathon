import { useRef, useCallback, useEffect, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceRadial, forceCollide, forceManyBody } from "d3-force";
import { getExtColor } from "./data/theme";

const nodeRadius = (node) => {
  const base = node.type === "folder" ? 10 : 5;
  return base + node.importance * 8;
};

// ── Deterministic pseudo-random (seeded) ──
function seededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ── Pre-generate star field ──
const STAR_COUNT = 300;
const starSeed = seededRandom(42);
const STARS = Array.from({ length: STAR_COUNT }, () => ({
  x: (starSeed() - 0.5) * 4000,
  y: (starSeed() - 0.5) * 4000,
  r: starSeed() * 1.2 + 0.3,
  opacity: starSeed() * 0.6 + 0.15,
  twinkleSpeed: starSeed() * 0.003 + 0.001,
  twinklePhase: starSeed() * Math.PI * 2,
}));

// ── Cluster hull colors per group ──
const GROUP_HULL_COLORS = {
  pulmonary:   { r: 60, g: 140, b: 255, a: 0.08 },
  infectious:  { r: 255, g: 80, b: 80, a: 0.07 },
  cardiac:     { r: 255, g: 50, b: 120, a: 0.07 },
  surgical:    { r: 80, g: 220, b: 150, a: 0.07 },
  diagnostic:  { r: 170, g: 120, b: 255, a: 0.06 },
};

// ── Convex hull (monotone chain) ──
function convexHull(points) {
  if (points.length <= 2) return [...points];
  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (O, A, B) =>
    (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x);
  const lower = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0)
      lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], sorted[i]) <= 0)
      upper.pop();
    upper.push(sorted[i]);
  }
  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

// ── Expand hull outward from centroid ──
function expandHull(hull, padding) {
  if (hull.length === 0) return hull;
  const cx = hull.reduce((s, p) => s + p.x, 0) / hull.length;
  const cy = hull.reduce((s, p) => s + p.y, 0) / hull.length;
  return hull.map((p) => {
    const dx = p.x - cx;
    const dy = p.y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    return { x: p.x + (dx / dist) * padding, y: p.y + (dy / dist) * padding };
  });
}

// ── Draw smooth closed shape through hull points ──
function drawSmoothHull(ctx, hull) {
  if (hull.length < 3) return;
  ctx.beginPath();
  // Start at midpoint of first edge
  const mid = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
  const start = mid(hull[hull.length - 1], hull[0]);
  ctx.moveTo(start.x, start.y);
  for (let i = 0; i < hull.length; i++) {
    const curr = hull[i];
    const next = hull[(i + 1) % hull.length];
    const m = mid(curr, next);
    ctx.quadraticCurveTo(curr.x, curr.y, m.x, m.y);
  }
  ctx.closePath();
}

// ── Particle config ──
const PARTICLES_PER_LINK = 2;
const PARTICLE_SPEED = 0.004;
const PARTICLE_RADIUS = 1.4;

// ── Pre-generate nebula clouds ──
const NEBULAE = [
  { x: -200, y: -150, radius: 500, color: [100, 40, 200], opacity: 0.35 },
  { x: 220, y: 80,   radius: 450, color: [30, 90, 200],  opacity: 0.30 },
  { x: -60, y: 250,  radius: 400, color: [20, 160, 180],  opacity: 0.25 },
  { x: 350, y: -220, radius: 360, color: [180, 30, 120],  opacity: 0.22 },
  { x: -350, y: 60,  radius: 420, color: [50, 60, 200],   opacity: 0.20 },
  { x: 50,  y: -50,  radius: 550, color: [60, 30, 140],   opacity: 0.18 },
];

export default function ConstellationGraph({
  graphData,
  neighborMap,
  hoveredNode,
  selectedNodeId,
  onHoverNode,
  onClickNode,
  onZoomChange,
  width,
  height,
}) {
  const graphRef = useRef(null);
  const graphDataRef = useRef(graphData);
  graphDataRef.current = graphData;
  const frameRef = useRef(0);
  const nodeBirthRef = useRef({});
  const groupCentroidsRef = useRef({});

  // Refs for paint callbacks — avoids recreating callbacks on every hover
  const hoverRef = useRef(null);
  const selectedRef = useRef(null);
  const neighborSetRef = useRef(new Set());

  // Compute neighbor set for current hover
  const neighborSet = useMemo(() => {
    if (hoveredNode == null) return new Set();
    const s = new Set([hoveredNode]);
    const nbs = neighborMap?.get(hoveredNode);
    if (nbs) nbs.forEach((n) => s.add(n));
    return s;
  }, [hoveredNode, neighborMap]);

  hoverRef.current = hoveredNode;
  selectedRef.current = selectedNodeId;
  neighborSetRef.current = neighborSet;

  // ── Configure d3 forces ──
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;

    fg.d3Force(
      "radial",
      forceRadial(
        (node) => {
          if (node.type === "folder") return 60 + (1 - node.importance) * 80;
          return 120 + (1 - node.importance) * 280;
        },
        0,
        0
      ).strength((node) => 0.3 + node.importance * 0.5)
    );

    fg.d3Force(
      "collide",
      forceCollide()
        .radius((node) => nodeRadius(node) + 6)
        .strength(0.9)
        .iterations(3)
    );

    fg.d3Force("charge", forceManyBody().strength(-40).distanceMax(350));

    const lf = fg.d3Force("link");
    if (lf) lf.distance(80).strength(0.15);

    fg.d3Force("center", null);
    fg.d3ReheatSimulation();
  }, []);

  // Center on selected node when it changes
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg || !selectedNodeId) return;
    const node = graphData.nodes.find((n) => n.id === selectedNodeId);
    if (node && node.x != null) {
      fg.centerAt(node.x, node.y, 500);
      fg.zoom(2.2, 500);
    }
  }, [selectedNodeId, graphData.nodes]);

  // ── Node painter ──
  const paintNode = useCallback((node, ctx, globalScale) => {
    if (node.x == null || node.y == null) return;

    const r = nodeRadius(node);
    const color = getExtColor(node.ext);
    const isFolder = node.type === "folder";
    const hovered = hoverRef.current;
    const nSet = neighborSetRef.current;
    const selId = selectedRef.current;
    const t = frameRef.current;

    const dimmed = hovered != null && hovered !== node.id && !nSet.has(node.id);
    const isSelected = selId === node.id;

    // ── Semantic zoom: fade out low-importance files when zoomed out ──
    let zoomAlpha = 1;
    if (!isFolder && !isSelected) {
      if (globalScale < 1) {
        const threshold = 1.1 - globalScale; // 0.4 at scale=0.7, 0.8 at scale=0.3
        if (node.importance < threshold) {
          zoomAlpha = Math.max(0, node.importance / threshold);
        }
      }
    }
    if (zoomAlpha < 0.05) return;

    // ── Entrance animation ──
    if (!nodeBirthRef.current[node.id]) {
      nodeBirthRef.current[node.id] = t;
    }
    const age = t - nodeBirthRef.current[node.id];
    const entranceT = Math.min(age / 45, 1); // 45 frames (~0.75s)
    const easeOut = 1 - Math.pow(1 - entranceT, 3); // cubic ease-out
    const entranceScale = 0.2 + 0.8 * easeOut;
    const entranceAlpha = easeOut;
    const vr = r * entranceScale; // visual radius

    ctx.save();
    ctx.globalAlpha = (dimmed ? 0.12 : 1) * zoomAlpha * entranceAlpha;

    // ── Pulsing glow (selected: breathing, otherwise: static) ──
    const pulse = isSelected ? Math.sin(t * 0.06) * 0.35 + 1 : 1;
    const glowR = vr * (isFolder ? 3.5 : 2.5) * pulse;
    const grad = ctx.createRadialGradient(node.x, node.y, vr * 0.3, node.x, node.y, glowR);
    const glowIntensity = isSelected ? "88" : "66";
    grad.addColorStop(0, color + glowIntensity);
    grad.addColorStop(0.5, color + "22");
    grad.addColorStop(1, color + "00");
    ctx.beginPath();
    ctx.arc(node.x, node.y, glowR, 0, 2 * Math.PI);
    ctx.fillStyle = grad;
    ctx.fill();

    // Core
    ctx.beginPath();
    ctx.arc(node.x, node.y, vr, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = (isFolder ? 20 : 10) * (isSelected ? pulse : 1);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Specular
    const inner = ctx.createRadialGradient(
      node.x - vr * 0.25, node.y - vr * 0.25, 0,
      node.x, node.y, vr
    );
    inner.addColorStop(0, "#ffffff88");
    inner.addColorStop(0.4, "#ffffff22");
    inner.addColorStop(1, "#ffffff00");
    ctx.beginPath();
    ctx.arc(node.x, node.y, vr, 0, 2 * Math.PI);
    ctx.fillStyle = inner;
    ctx.fill();

    // Selection ring (rotating dash + pulsing radius)
    if (isSelected) {
      const ringR = vr + 3 + Math.sin(t * 0.06) * 1.5;
      ctx.beginPath();
      ctx.arc(node.x, node.y, ringR, 0, 2 * Math.PI);
      ctx.strokeStyle = `rgba(255,255,255,${0.4 + Math.sin(t * 0.04) * 0.15})`;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.lineDashOffset = -t * 0.5;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineDashOffset = 0;
    }

    // Label — fade out when zoomed out for nebula feel
    const labelAlpha = globalScale < 0.6 ? 0
                     : globalScale < 1.2 ? (globalScale - 0.6) / 0.6
                     : 1;
    if (labelAlpha > 0.01 && (!dimmed || isFolder || isSelected)) {
      const fontSize = Math.max(10 / globalScale, vr * 0.7);
      ctx.font = `${fontSize}px 'Inter', 'SF Pro', sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const baseAlpha = dimmed ? 0.27 : 0.8;
      ctx.fillStyle = `rgba(255,255,255,${(baseAlpha * labelAlpha).toFixed(2)})`;
      ctx.fillText(node.name, node.x, node.y + vr + 3);
    }

    ctx.restore();
  }, []);

  // ── Link painter (edge-bundled Bezier curves) ──
  const paintLink = useCallback((link, ctx) => {
    const source = typeof link.source === "object" ? link.source : null;
    const target = typeof link.target === "object" ? link.target : null;
    if (!source || !target || source.x == null || target.x == null) return;

    const hovered = hoverRef.current;
    const nSet = neighborSetRef.current;
    const dimmed = hovered != null && !nSet.has(source.id) && !nSet.has(target.id);

    // ── Compute Bezier control point (edge bundling) ──
    const centroids = groupCentroidsRef.current;
    const mx = (source.x + target.x) / 2;
    const my = (source.y + target.y) / 2;
    let cpx, cpy;
    if (source.group && source.group === target.group && centroids[source.group]) {
      // Same group: curve toward group centroid
      const c = centroids[source.group];
      cpx = mx + (c.x - mx) * 0.4;
      cpy = my + (c.y - my) * 0.4;
    } else {
      // Cross-group: offset perpendicular to make it visually distinct
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      cpx = mx + (-dy / len) * 25;
      cpy = my + (dx / len) * 25;
    }

    ctx.save();
    ctx.globalAlpha = dimmed ? 0.04 : 0.3;
    ctx.strokeStyle = "#4488ff";
    ctx.lineWidth = dimmed ? 0.3 : 0.8;
    ctx.shadowColor = "#4488ff";
    ctx.shadowBlur = dimmed ? 0 : 6;
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.quadraticCurveTo(cpx, cpy, target.x, target.y);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // ── Animated particles (follow Bezier curve) ──
    if (!dimmed) {
      const t = frameRef.current;
      for (let i = 0; i < PARTICLES_PER_LINK; i++) {
        const phase = i / PARTICLES_PER_LINK;
        const p = (t * PARTICLE_SPEED + phase) % 1;
        // Quadratic Bezier: B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
        const omp = 1 - p;
        const px = omp * omp * source.x + 2 * omp * p * cpx + p * p * target.x;
        const py = omp * omp * source.y + 2 * omp * p * cpy + p * p * target.y;
        ctx.beginPath();
        ctx.arc(px, py, PARTICLE_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(140,200,255,${(0.5 + p * 0.4).toFixed(2)})`;
        ctx.fill();
      }
    }
    ctx.restore();
  }, []);

  const paintPointerArea = useCallback((node, color, ctx) => {
    if (node.x == null || node.y == null) return;
    const r = nodeRadius(node);
    ctx.beginPath();
    ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }, []);

  // ── Background: Nebula clouds + Star field + Cluster hulls ──
  const paintBackground = useCallback((ctx, globalScale) => {
    frameRef.current += 1;
    const t = frameRef.current;

    // ── Nebula clouds (screen blend for luminous glow) ──
    ctx.save();
    ctx.globalCompositeOperation = "screen";
    for (const neb of NEBULAE) {
      const grad = ctx.createRadialGradient(
        neb.x, neb.y, 0,
        neb.x, neb.y, neb.radius
      );
      const [r, g, b] = neb.color;
      grad.addColorStop(0,   `rgba(${r},${g},${b},${neb.opacity})`);
      grad.addColorStop(0.2, `rgba(${r},${g},${b},${neb.opacity * 0.7})`);
      grad.addColorStop(0.5, `rgba(${r},${g},${b},${neb.opacity * 0.3})`);
      grad.addColorStop(0.8, `rgba(${r},${g},${b},${neb.opacity * 0.08})`);
      grad.addColorStop(1,   `rgba(${r},${g},${b},0)`);
      ctx.beginPath();
      ctx.arc(neb.x, neb.y, neb.radius, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
    }
    ctx.restore();

    // ── Star field ──
    for (const star of STARS) {
      const twinkle = Math.sin(t * star.twinkleSpeed + star.twinklePhase) * 0.3 + 0.7;
      const alpha = star.opacity * twinkle;
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.r / globalScale, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(220,230,255,${alpha.toFixed(3)})`;
      ctx.fill();
    }

    // ── Cluster hulls + compute group centroids for edge bundling ──
    const nodes = graphDataRef.current?.nodes;
    if (nodes && nodes.length > 0) {
      // Group nodes by cluster
      const groups = {};
      for (const node of nodes) {
        if (node.x == null || node.y == null || !node.group) continue;
        if (!groups[node.group]) groups[node.group] = [];
        groups[node.group].push({ x: node.x, y: node.y });
      }

      // Store centroids for edge bundling (used by paintLink)
      const centroids = {};
      for (const [gn, pts] of Object.entries(groups)) {
        centroids[gn] = {
          x: pts.reduce((s, p) => s + p.x, 0) / pts.length,
          y: pts.reduce((s, p) => s + p.y, 0) / pts.length,
        };
      }
      groupCentroidsRef.current = centroids;

      ctx.save();
      for (const [groupName, pts] of Object.entries(groups)) {
        if (pts.length < 3) continue;
        const hullColor = GROUP_HULL_COLORS[groupName];
        if (!hullColor) continue;

        const hull = convexHull(pts);
        if (hull.length < 3) continue;
        const expanded = expandHull(hull, 35);

        // Filled hull
        drawSmoothHull(ctx, expanded);
        const { r, g, b, a } = hullColor;
        ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
        ctx.fill();

        // Hull border glow
        drawSmoothHull(ctx, expanded);
        ctx.strokeStyle = `rgba(${r},${g},${b},${a * 2.5})`;
        ctx.lineWidth = 1;
        ctx.shadowColor = `rgba(${r},${g},${b},0.4)`;
        ctx.shadowBlur = 12;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
      ctx.restore();
    }
  }, []);

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={graphData}
      nodeId="id"
      width={width}
      height={height}
      backgroundColor="#05050a"
      nodeCanvasObject={paintNode}
      nodeCanvasObjectMode={() => "replace"}
      nodePointerAreaPaint={paintPointerArea}
      linkCanvasObject={paintLink}
      linkCanvasObjectMode={() => "replace"}
      onRenderFramePre={paintBackground}
      onNodeHover={(node) => onHoverNode(node?.id ?? null)}
      onNodeClick={(node) => onClickNode(node)}
      onBackgroundClick={() => {
        const fg = graphRef.current;
        if (fg) {
          fg.centerAt(0, 0, 500);
          fg.zoom(1, 500);
        }
      }}
      onZoom={({ k }) => onZoomChange?.(k)}
      cooldownTime={Infinity}
      warmupTicks={100}
      d3AlphaDecay={0.02}
      d3AlphaMin={0}
      d3VelocityDecay={0.3}
      enableNodeDrag={true}
      minZoom={0.3}
      maxZoom={8}
    />
  );
}
