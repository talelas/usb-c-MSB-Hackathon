import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import ConstellationGraph from "./ConstellationGraph";
import TopBar from "./components/TopBar";
import LeftSidebar from "./components/LeftSidebar";
import RightSidebar from "./components/RightSidebar";
import ChatPanel from "./components/ChatPanel";
import IngestPanel from "./components/IngestPanel";
import SearchBar from "./components/SearchBar";
import StatusBar from "./components/StatusBar";
import { fetchDocuments, searchDocuments } from "./data/api";
import { buildGraphData, buildNeighborMap } from "./data/graphTransforms";
import { COLORS } from "./data/theme";

const LEFT_WIDTH = 240;
const RIGHT_WIDTH = 400;

export default function App() {
  // ── State ──
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [openTabs, setOpenTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [showRight, setShowRight] = useState(false);
  const [rightPanelMode, setRightPanelMode] = useState("document"); // "document", "chat", or "ingest"
  const [zoom, setZoom] = useState(1);
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphLinks, setGraphLinks] = useState([]);
  const [fileTree, setFileTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchError, setSearchError] = useState(null);

  // Center panel ref for measuring
  const centerRef = useRef(null);
  const [centerSize, setCenterSize] = useState({ width: 800, height: 600 });

  // Graph data (stable reference)
  const graphData = useMemo(
    () => ({ nodes: [...graphNodes], links: [...graphLinks] }),
    [graphNodes, graphLinks]
  );

  const neighborMap = useMemo(
    () => buildNeighborMap(graphLinks),
    [graphLinks]
  );

  const docNodeById = useMemo(() => {
    const map = new Map();
    graphNodes.forEach((node) => {
      if (node.type === "file" && node.docId != null) {
        map.set(node.docId, node);
      }
    });
    return map;
  }, [graphNodes]);

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

  useEffect(() => {
    let isMounted = true;

    const loadDocuments = async () => {
      setLoading(true);
      setError(null);
      try {
        const docs = await fetchDocuments();
        if (!isMounted) return;
        const { nodes, links, fileTree: tree } = buildGraphData(docs || []);
        setGraphNodes(nodes);
        setGraphLinks(links);
        setFileTree(tree);
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || "Failed to load documents");
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadDocuments();

    return () => {
      isMounted = false;
    };
  }, []);

  // Function to reload documents (called after ingestion)
  const reloadDocuments = useCallback(async () => {
    console.log('[App] Reloading documents after ingestion...');
    setLoading(true);
    setError(null);
    try {
      const docs = await fetchDocuments();
      const { nodes, links, fileTree: tree } = buildGraphData(docs || []);
      setGraphNodes(nodes);
      setGraphLinks(links);
      setFileTree(tree);
      console.log('[App] Documents reloaded successfully');
    } catch (err) {
      setError(err.message || "Failed to reload documents");
      console.error('[App] Failed to reload documents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Handlers ──
  const handleSelectNode = useCallback((node) => {
    setSelectedNode(node);
    setShowRight(true);
    setRightPanelMode("document");

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
        setRightPanelMode("document");
      }
    },
    [graphNodes]
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
    [activeTabId, graphNodes]
  );

  const handleCloseRight = useCallback(() => {
    setShowRight(false);
    setSelectedNode(null);
    setActiveTabId(null);
  }, []);

  const handleToggleChat = useCallback(() => {
    if (showRight && rightPanelMode === "chat") {
      setShowRight(false);
    } else {
      setShowRight(true);
      setRightPanelMode("chat");
    }
  }, [showRight, rightPanelMode]);

  const handleToggleIngest = useCallback(() => {
    if (showRight && rightPanelMode === "ingest") {
      setShowRight(false);
    } else {
      setShowRight(true);
      setRightPanelMode("ingest");
    }
  }, [showRight, rightPanelMode]);

  const handleSearch = useCallback(
    async (query) => {
      setSearchQuery(query);
      setSearchResults([]);
      setSearchError(null);
      try {
        const response = await searchDocuments(query);
        const results = response?.results || [];
        setSearchResults(results);
        if (results.length > 0) {
          const top = docNodeById.get(results[0].doc_id);
          if (top) {
            handleSelectNode(top);
          } else {
            setShowRight(true);
          }
        } else {
          setShowRight(true);
        }
      } catch (err) {
        setSearchResults([]);
        setSearchError(err.message || "Search failed");
        setShowRight(true);
      }
    },
    [docNodeById, handleSelectNode]
  );

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
          fileTree={fileTree}
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

          {(loading || error) && (
            <div style={styles.centerOverlay}>
              <div style={styles.centerCard}>
                <div style={styles.centerTitle}>
                  {loading ? "Loading documents..." : "Failed to load"}
                </div>
                {error && <div style={styles.centerSub}>{error}</div>}
              </div>
            </div>
          )}

          {/* Search bar overlay */}
          <SearchBar
            onSelectNode={handleSelectNode}
            onSearch={handleSearch}
            graphNodes={graphNodes}
          />

          {/* Chat toggle button */}
          <button
            style={{
              ...styles.chatToggle,
              background: showRight && rightPanelMode === "chat" ? COLORS.accent : COLORS.bgPanel,
              color: showRight && rightPanelMode === "chat" ? COLORS.bg : COLORS.text,
            }}
            onClick={handleToggleChat}
            title="Toggle AI Chat"
          >
            💬
          </button>

          {/* Ingest toggle button */}
          <button
            style={{
              ...styles.ingestToggle,
              background: showRight && rightPanelMode === "ingest" ? COLORS.accentGreen : COLORS.bgPanel,
              color: showRight && rightPanelMode === "ingest" ? COLORS.bg : COLORS.text,
            }}
            onClick={handleToggleIngest}
            title="Ingest Documents"
          >
            ➕
          </button>
        </div>

        {/* Right Sidebar - Document, Chat, or Ingest */}
        {showRight && (
          <>
            {rightPanelMode === "document" ? (
              <RightSidebar
                selectedNode={selectedNode}
                neighborMap={neighborMap}
                onSelectNode={handleSelectNode}
                onClose={handleCloseRight}
                fileTree={fileTree}
                graphNodes={graphNodes}
                searchResults={searchResults}
                searchQuery={searchQuery}
                searchError={searchError}
                width={RIGHT_WIDTH}
              />
            ) : rightPanelMode === "chat" ? (
              <ChatPanel
                sessionId="default"
                onClose={handleCloseRight}
                width={RIGHT_WIDTH}
              />
            ) : (
              <IngestPanel
                onClose={handleCloseRight}
                onIngestComplete={reloadDocuments}
                width={RIGHT_WIDTH}
              />
            )}
          </>
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
  centerOverlay: {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    pointerEvents: "none",
    zIndex: 10,
  },
  centerCard: {
    background: "#0c0c22cc",
    border: `1px solid ${COLORS.border}`,
    borderRadius: 12,
    padding: "14px 18px",
    textAlign: "center",
    boxShadow: "0 10px 30px #00000066",
  },
  centerTitle: {
    color: COLORS.text,
    fontSize: 14,
    fontWeight: 600,
  },
  centerSub: {
    color: COLORS.textMuted,
    fontSize: 12,
    marginTop: 6,
  },
  chatToggle: {
    position: "absolute",
    top: 24,
    right: 24,
    width: 50,
    height: 50,
    borderRadius: "50%",
    border: `1px solid ${COLORS.border}`,
    backdropFilter: "blur(16px)",
    fontSize: 24,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.2s",
    boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    zIndex: 20,
  },
  ingestToggle: {
    position: "absolute",
    bottom: 90,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: "50%",
    border: `1px solid ${COLORS.border}`,
    backdropFilter: "blur(16px)",
    fontSize: 28,
    fontWeight: "bold",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.2s",
    boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
    zIndex: 20,
  },
};
