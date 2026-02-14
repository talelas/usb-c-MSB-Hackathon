import { useRef, useCallback, useEffect, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceRadial, forceCollide, forceManyBody } from "d3-force";
import { getExtColor } from "./data/theme";

const nodeRadius = (node) => {
  const base = node.type === "folder" ? 10 : 5;
  return base + node.importance * 8;
};

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

    const dimmed = hovered != null && hovered !== node.id && !nSet.has(node.id);
    const isSelected = selId === node.id;

    ctx.save();
    ctx.globalAlpha = dimmed ? 0.12 : 1;

    // Glow halo
    const glowR = r * (isFolder ? 3.5 : 2.5);
    const grad = ctx.createRadialGradient(node.x, node.y, r * 0.3, node.x, node.y, glowR);
    grad.addColorStop(0, color + "66");
    grad.addColorStop(0.5, color + "22");
    grad.addColorStop(1, color + "00");
    ctx.beginPath();
    ctx.arc(node.x, node.y, glowR, 0, 2 * Math.PI);
    ctx.fillStyle = grad;
    ctx.fill();

    // Core
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = isFolder ? 20 : 10;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Specular
    const inner = ctx.createRadialGradient(
      node.x - r * 0.25, node.y - r * 0.25, 0,
      node.x, node.y, r
    );
    inner.addColorStop(0, "#ffffff88");
    inner.addColorStop(0.4, "#ffffff22");
    inner.addColorStop(1, "#ffffff00");
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = inner;
    ctx.fill();

    // Selection ring
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI);
      ctx.strokeStyle = "#ffffff88";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Label
    if (!dimmed || isFolder || isSelected) {
      const fontSize = Math.max(10 / globalScale, r * 0.7);
      ctx.font = `${fontSize}px 'Inter', 'SF Pro', sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = dimmed ? "#ffffff44" : "#ffffffcc";
      ctx.fillText(node.name, node.x, node.y + r + 3);
    }

    ctx.restore();
  }, []);

  // ── Link painter ──
  const paintLink = useCallback((link, ctx) => {
    const source = typeof link.source === "object" ? link.source : null;
    const target = typeof link.target === "object" ? link.target : null;
    if (!source || !target || source.x == null || target.x == null) return;

    const hovered = hoverRef.current;
    const nSet = neighborSetRef.current;
    const dimmed = hovered != null && !nSet.has(source.id) && !nSet.has(target.id);

    ctx.save();
    ctx.globalAlpha = dimmed ? 0.04 : 0.3;
    ctx.strokeStyle = "#4488ff";
    ctx.lineWidth = dimmed ? 0.3 : 0.8;
    ctx.shadowColor = "#4488ff";
    ctx.shadowBlur = dimmed ? 0 : 6;
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
    ctx.shadowBlur = 0;
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
      cooldownTime={4000}
      warmupTicks={100}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.3}
      enableNodeDrag={true}
      minZoom={0.3}
      maxZoom={8}
    />
  );
}
