import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import ConstellationGraph from "./ConstellationGraph";
import TopBar from "./components/TopBar";
import LeftSidebar from "./components/LeftSidebar";
import RightSidebar from "./components/RightSidebar";
import SearchBar from "./components/SearchBar";
import StatusBar from "./components/StatusBar";
import { graphNodes, graphLinks, buildNeighborMap } from "./data/mockData";
import { COLORS } from "./data/theme";

const LEFT_WIDTH = 240;
const RIGHT_WIDTH = 300;

export default function App() {
  // ── State ──
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [openTabs, setOpenTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [showRight, setShowRight] = useState(false);
  const [zoom, setZoom] = useState(1);

  // Center panel ref for measuring
  const centerRef = useRef(null);
  const [centerSize, setCenterSize] = useState({ width: 800, height: 600 });

  // Graph data (stable reference)
  const graphData = useMemo(
    () => ({ nodes: [...graphNodes], links: [...graphLinks] }),
    []
  );

  const neighborMap = useMemo(
    () => buildNeighborMap(graphLinks),
    []
  );

  // Resize observer for center panel
  useEffect(() => {
    const el = centerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setCenterSize({ width: Math.floor(width), height: Math.floor(height) });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [showRight]);

  // ── Handlers ──
  const handleSelectNode = useCallback((node) => {
    setSelectedNode(node);
    setShowRight(true);

    // Add to tabs if not already open
    setOpenTabs((prev) => {
      if (prev.some((t) => t.id === node.id)) return prev;
      return [...prev, { id: node.id, name: node.name, ext: node.ext }];
    });
    setActiveTabId(node.id);
  }, []);

  const handleTabClick = useCallback(
    (id) => {
      setActiveTabId(id);
      const node = graphNodes.find((n) => n.id === id);
      if (node) {
        setSelectedNode(node);
        setShowRight(true);
      }
    },
    []
  );

  const handleTabClose = useCallback(
    (id) => {
      setOpenTabs((prev) => {
        const next = prev.filter((t) => t.id !== id);
        if (activeTabId === id) {
          const newActive = next.length > 0 ? next[next.length - 1].id : null;
          setActiveTabId(newActive);
          if (newActive) {
            const node = graphNodes.find((n) => n.id === newActive);
            if (node) setSelectedNode(node);
          } else {
            setSelectedNode(null);
            setShowRight(false);
          }
        }
        return next;
      });
    },
    [activeTabId]
  );

  const handleCloseRight = useCallback(() => {
    setShowRight(false);
    setSelectedNode(null);
    setActiveTabId(null);
  }, []);

  const handleSearch = useCallback((query) => {
    // Placeholder for backend semantic search
    console.log("Semantic search:", query);
    alert(`Semantic search will be sent to backend:\n\n"${query}"\n\n(Backend not connected yet)`);
  }, []);

  return (
    <div style={styles.shell}>
      {/* Top Bar */}
      <TopBar
        openTabs={openTabs}
        activeTabId={activeTabId}
        onTabClick={handleTabClick}
        onTabClose={handleTabClose}
      />

      {/* Main area */}
      <div style={styles.main}>
        {/* Left Sidebar */}
        <LeftSidebar
          selectedNodeId={selectedNode?.id}
          onSelectNode={handleSelectNode}
          width={LEFT_WIDTH}
        />

        {/* Center: Graph + Search */}
        <div ref={centerRef} style={styles.center}>
          <ConstellationGraph
            graphData={graphData}
            neighborMap={neighborMap}
            hoveredNode={hoveredNode}
            selectedNodeId={selectedNode?.id}
            onHoverNode={setHoveredNode}
            onClickNode={handleSelectNode}
            onZoomChange={setZoom}
            width={centerSize.width}
            height={centerSize.height}
          />

          {/* Search bar overlay */}
          <SearchBar
            onSelectNode={handleSelectNode}
            onSearch={handleSearch}
          />
        </div>

        {/* Right Sidebar */}
        {showRight && (
          <RightSidebar
            selectedNode={selectedNode}
            neighborMap={neighborMap}
            onSelectNode={handleSelectNode}
            onClose={handleCloseRight}
            width={RIGHT_WIDTH}
          />
        )}
      </div>

      {/* Status Bar */}
      <StatusBar
        nodeCount={graphNodes.length}
        linkCount={graphLinks.length}
        selectedNode={selectedNode}
        zoom={zoom}
      />
    </div>
  );
}

const styles = {
  shell: {
    width: "100vw",
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    background: COLORS.bg,
    overflow: "hidden",
    fontFamily: "'Inter', 'SF Pro', system-ui, sans-serif",
  },
  main: {
    flex: 1,
    display: "flex",
    overflow: "hidden",
    minHeight: 0,
  },
  center: {
    flex: 1,
    position: "relative",
    overflow: "hidden",
    minWidth: 0,
  },
};
