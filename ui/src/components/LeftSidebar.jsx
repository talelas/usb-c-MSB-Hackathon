import { useEffect, useMemo, useState } from "react";
import { COLORS, getExtColor, getExtIcon } from "../data/theme";

// ─── Tree Item (recursive) ──────────────────────────────────────────
function TreeItem({ item, depth, selectedId, onSelect, expandedIds, onToggleExpand }) {
  const isFolder = item.type === "folder";
  const isExpanded = expandedIds.has(item.id);
  const isSelected = selectedId === item.id;
  const color = getExtColor(item.ext);
  const icon = getExtIcon(item.ext);

  return (
    <>
      <div
        style={{
          ...styles.item,
          paddingLeft: 12 + depth * 14,
          background: isSelected ? COLORS.bgActive : "transparent",
          color: isSelected ? COLORS.text : COLORS.textDim,
        }}
        onClick={() => {
          if (isFolder) onToggleExpand(item.id);
          onSelect(item);
        }}
        onMouseEnter={(e) => {
          if (!isSelected) e.currentTarget.style.background = COLORS.bgHover;
        }}
        onMouseLeave={(e) => {
          if (!isSelected) e.currentTarget.style.background = "transparent";
        }}
      >
        {/* Expand arrow for folders */}
        <span style={{ ...styles.arrow, opacity: isFolder ? 1 : 0 }}>
          {isFolder ? (isExpanded ? "▾" : "▸") : ""}
        </span>
        <span style={{ fontSize: 13, marginRight: 5 }}>{icon}</span>
        <span style={styles.name}>{item.name}</span>
        {/* Importance dot */}
        <span
          style={{
            ...styles.importanceDot,
            background: color,
            opacity: 0.3 + item.importance * 0.7,
            width: 4 + item.importance * 4,
            height: 4 + item.importance * 4,
          }}
        />
      </div>

      {/* Children */}
      {isFolder && isExpanded && item.children && (
        <div>
          {item.children.map((child) => (
            <TreeItem
              key={child.id}
              item={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </div>
      )}
    </>
  );
}

// ─── Left Sidebar ───────────────────────────────────────────────────
export default function LeftSidebar({ selectedNodeId, onSelectNode, fileTree = [], width }) {
  const [activeTab, setActiveTab] = useState("explorer");
  const [expandedIds, setExpandedIds] = useState(
    new Set(fileTree.map((f) => f.id))
  );
  const [filterText, setFilterText] = useState("");
  const [minImportance, setMinImportance] = useState(0);

  useEffect(() => {
    setExpandedIds(new Set(fileTree.map((f) => f.id)));
  }, [fileTree]);

  const onToggleExpand = (id) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Filter the tree
  const filteredTree = useMemo(() => {
    if (!filterText && minImportance === 0) return fileTree;

    const lc = filterText.toLowerCase();
    return fileTree
      .map((folder) => {
        if (!folder.children) return folder;
        const filteredChildren = folder.children.filter((child) => {
          const nameMatch = !filterText || child.name.toLowerCase().includes(lc);
          const impMatch = child.importance >= minImportance;
          return nameMatch && impMatch;
        });
        return { ...folder, children: filteredChildren };
      })
      .filter((folder) => {
        if (folder.type === "folder") {
          const folderNameMatch = !filterText || folder.name.toLowerCase().includes(lc);
          return folderNameMatch || (folder.children && folder.children.length > 0);
        }
        return true;
      });
  }, [filterText, minImportance]);

  return (
    <div style={{ ...styles.sidebar, width }}>
      {/* Tab headers */}
      <div style={styles.tabRow}>
        {[
          { key: "explorer", label: "📂 Explorer" },
          { key: "bookmarks", label: "🔖 Bookmarks" },
          { key: "recent", label: "🕐 Recent" },
        ].map((tab) => (
          <button
            key={tab.key}
            style={{
              ...styles.tabBtn,
              ...(activeTab === tab.key ? styles.tabBtnActive : {}),
            }}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "explorer" && (
        <>
          {/* Filter bar */}
          <div style={styles.filterRow}>
            <input
              type="text"
              placeholder="Filter files..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              style={styles.filterInput}
            />
          </div>

          {/* Importance slider */}
          <div style={styles.sliderRow}>
            <span style={styles.sliderLabel}>Min importance</span>
            <input
              type="range"
              min={0}
              max={100}
              value={minImportance * 100}
              onChange={(e) => setMinImportance(e.target.value / 100)}
              style={styles.slider}
            />
            <span style={styles.sliderValue}>{(minImportance * 100).toFixed(0)}%</span>
          </div>

          {/* Tree */}
          <div style={styles.treeContainer}>
            {filteredTree.map((item) => (
              <TreeItem
                key={item.id}
                item={item}
                depth={0}
                selectedId={selectedNodeId}
                onSelect={onSelectNode}
                expandedIds={expandedIds}
                onToggleExpand={onToggleExpand}
              />
            ))}
          </div>
        </>
      )}

      {activeTab === "bookmarks" && (
        <div style={styles.placeholder}>
          <span style={{ fontSize: 28 }}>🔖</span>
          <span style={{ color: COLORS.textMuted, fontSize: 12 }}>
            No bookmarks yet
          </span>
          <span style={{ color: COLORS.textFaint, fontSize: 11 }}>
            Right-click a node to bookmark
          </span>
        </div>
      )}

      {activeTab === "recent" && (
        <div style={styles.placeholder}>
          <span style={{ fontSize: 28 }}>🕐</span>
          <span style={{ color: COLORS.textMuted, fontSize: 12 }}>
            Recently opened files will show here
          </span>
        </div>
      )}
    </div>
  );
}

const styles = {
  sidebar: {
    background: COLORS.bgPanel,
    borderRight: `1px solid ${COLORS.border}`,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    height: "100%",
  },
  tabRow: {
    display: "flex",
    borderBottom: `1px solid ${COLORS.border}`,
    padding: "0 2px",
  },
  tabBtn: {
    flex: 1,
    background: "none",
    border: "none",
    color: COLORS.textMuted,
    fontSize: 10,
    padding: "8px 4px",
    cursor: "pointer",
    borderBottom: "2px solid transparent",
    whiteSpace: "nowrap",
  },
  tabBtnActive: {
    color: COLORS.accentCyan,
    borderBottomColor: COLORS.accentCyan,
  },
  filterRow: {
    padding: "8px 8px 4px",
  },
  filterInput: {
    width: "100%",
    background: COLORS.bgInput,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 6,
    color: COLORS.text,
    fontSize: 12,
    padding: "6px 10px",
    outline: "none",
  },
  sliderRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 10px 8px",
  },
  sliderLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
    whiteSpace: "nowrap",
  },
  slider: {
    flex: 1,
    accentColor: COLORS.accentCyan,
    height: 3,
  },
  sliderValue: {
    fontSize: 10,
    color: COLORS.textDim,
    minWidth: 28,
    textAlign: "right",
  },
  treeContainer: {
    flex: 1,
    overflowY: "auto",
    overflowX: "hidden",
    paddingBottom: 20,
  },
  item: {
    display: "flex",
    alignItems: "center",
    gap: 2,
    padding: "4px 8px",
    cursor: "pointer",
    fontSize: 12,
    transition: "background 0.1s",
    userSelect: "none",
  },
  arrow: {
    width: 14,
    fontSize: 10,
    color: COLORS.textMuted,
    textAlign: "center",
    flexShrink: 0,
  },
  name: {
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  importanceDot: {
    borderRadius: "50%",
    flexShrink: 0,
  },
  placeholder: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
};
