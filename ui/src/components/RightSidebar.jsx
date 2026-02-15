import { useMemo } from "react";
import { COLORS, getExtColor, getExtIcon } from "../data/theme";

export default function RightSidebar({
  selectedNode,
  neighborMap,
  onSelectNode,
  onClose,
  fileTree = [],
  graphNodes = [],
  searchResults = [],
  searchQuery = "",
  searchError = null,
  width,
}) {
  if (!selectedNode) {
    return (
      <div style={{ ...styles.sidebar, width }}>
        <div style={styles.empty}>
          <span style={{ fontSize: 36, opacity: 0.4 }}>◇</span>
          <span style={{ color: COLORS.textMuted, fontSize: 12 }}>
            Select a node to inspect
          </span>
          <span style={{ color: COLORS.textFaint, fontSize: 11 }}>
            Click on the graph or file tree
          </span>
        </div>
        {(searchError || searchResults.length > 0) && (
          <div style={{ ...styles.contentArea, paddingTop: 0 }}>
            <div style={styles.section}>
              <div style={styles.sectionTitle}>
                Search results{searchQuery ? ` for "${searchQuery}"` : ""}
              </div>
              {searchError && (
                <div style={styles.searchError}>{searchError}</div>
              )}
              {searchResults.map((result) => {
                const node = graphNodes.find((n) => n.docId === result.doc_id);
                const label = node?.name || result.file_name || `Doc ${result.doc_id}`;
                const ext = node?.ext || "txt";
                return (
                  <div
                    key={result.doc_id}
                    style={styles.relatedRow}
                    onClick={() => node && onSelectNode(node)}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = COLORS.bgHover)
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <span style={{ marginRight: 5, fontSize: 12 }}>
                      {getExtIcon(ext)}
                    </span>
                    <span style={{ color: getExtColor(ext), flex: 1 }}>
                      {label}
                    </span>
                    <span style={styles.fileMeta}>
                      {(result.final_score * 100).toFixed(0)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  }

  const isFolder = selectedNode.type === "folder";
  const color = getExtColor(selectedNode.ext);
  const icon = getExtIcon(selectedNode.ext);

  // For folders: get children from fileTree
  const folderChildren = useMemo(() => {
    if (!isFolder) return [];
    const folder = fileTree.find((f) => f.id === selectedNode.id);
    return folder?.children || [];
  }, [selectedNode.id, isFolder]);

  // File content
  const content = selectedNode.summary || selectedNode.chunk_text || null;

  // Connected nodes
  const connectedNodes = useMemo(() => {
    const ids = neighborMap?.get(selectedNode.id);
    if (!ids) return [];
    return Array.from(ids)
      .map((id) => graphNodes.find((n) => n.id === id))
      .filter(Boolean);
  }, [selectedNode.id, neighborMap]);

  // Breadcrumb
  const breadcrumb = useMemo(() => {
    const parentFolder = fileTree.find((f) =>
      f.children?.some((c) => c.id === selectedNode.id)
    );
    if (parentFolder) return [parentFolder.name, selectedNode.name];
    return [selectedNode.name];
  }, [selectedNode.id, selectedNode.name]);

  return (
    <div style={{ ...styles.sidebar, width }}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <span style={{ fontSize: 16 }}>{icon}</span>
          <span style={{ ...styles.headerName, color }}>{selectedNode.name}</span>
          <button style={styles.closeBtn} onClick={onClose}>
            ✕
          </button>
        </div>
        {/* Breadcrumb */}
        <div style={styles.breadcrumb}>
          {breadcrumb.map((seg, i) => (
            <span key={i}>
              {i > 0 && <span style={{ margin: "0 4px", color: COLORS.textFaint }}>›</span>}
              <span style={{ color: i === breadcrumb.length - 1 ? COLORS.textDim : COLORS.textMuted }}>
                {seg}
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Content area */}
      <div style={styles.contentArea}>
        {isFolder ? (
          /* ─── Folder: file listing ─── */
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              Contents ({folderChildren.length} files)
            </div>
            {folderChildren.map((child) => (
              <div
                key={child.id}
                style={styles.fileRow}
                onClick={() => onSelectNode(child)}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = COLORS.bgHover)
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <span style={{ marginRight: 6, fontSize: 13 }}>
                  {getExtIcon(child.ext)}
                </span>
                <span style={{ flex: 1, color: getExtColor(child.ext) }}>
                  {child.name}
                </span>
                <span style={styles.fileMeta}>
                  {(child.importance * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        ) : (
          /* ─── File: code preview ─── */
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Preview</div>
            {content ? (
              <pre style={styles.codeBlock}>{content}</pre>
            ) : (
              <div style={styles.noPreview}>
                <span style={{ fontSize: 24 }}>{icon}</span>
                <span style={{ color: COLORS.textMuted, fontSize: 12 }}>
                  No preview available for .{selectedNode.ext} files
                </span>
              </div>
            )}
            {selectedNode.keywords && selectedNode.keywords.length > 0 && (
              <div style={styles.keywordWrap}>
                {selectedNode.keywords.map((kw) => (
                  <span key={kw} style={styles.keyword}>
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ─── Details panel ─── */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Details</div>
          <div style={styles.detailGrid}>
            <DetailRow label="Type" value={isFolder ? "Folder" : `.${selectedNode.ext} file`} />
            <DetailRow
              label="Importance"
              value={
                <div style={styles.importanceBar}>
                  <div
                    style={{
                      ...styles.importanceFill,
                      width: `${selectedNode.importance * 100}%`,
                      background: color,
                    }}
                  />
                  <span style={styles.importanceText}>
                    {(selectedNode.importance * 100).toFixed(0)}%
                  </span>
                </div>
              }
            />
            <DetailRow label="Group" value={selectedNode.group} />
            <DetailRow
              label="Connections"
              value={`${neighborMap?.get(selectedNode.id)?.size ?? 0} nodes`}
            />
            {selectedNode.path && (
              <DetailRow label="Path" value={selectedNode.path} />
            )}
          </div>
        </div>

        {/* ─── Related nodes ─── */}
        {connectedNodes.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              Connected ({connectedNodes.length})
            </div>
            {connectedNodes.map((node) => {
              const isCrossProject = node.group !== selectedNode.group;
              return (
                <div
                  key={node.id}
                  style={styles.relatedRow}
                  onClick={() => onSelectNode(node)}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = COLORS.bgHover)
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <span style={{ marginRight: 5, fontSize: 12 }}>
                    {getExtIcon(node.ext)}
                  </span>
                  <span style={{ color: getExtColor(node.ext), flex: 1 }}>
                    {node.name}
                  </span>
                  {isCrossProject && (
                    <span style={styles.crossBadge}>cross</span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {searchResults.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              Search results{searchQuery ? ` for "${searchQuery}"` : ""}
            </div>
            {searchError && (
              <div style={styles.searchError}>{searchError}</div>
            )}
            {searchResults.map((result) => {
              const node = graphNodes.find((n) => n.docId === result.doc_id);
              const label = node?.name || result.file_name || `Doc ${result.doc_id}`;
              const ext = node?.ext || "txt";
              return (
                <div
                  key={result.doc_id}
                  style={styles.relatedRow}
                  onClick={() => node && onSelectNode(node)}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = COLORS.bgHover)
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <span style={{ marginRight: 5, fontSize: 12 }}>
                    {getExtIcon(ext)}
                  </span>
                  <span style={{ color: getExtColor(ext), flex: 1 }}>
                    {label}
                  </span>
                  <span style={styles.fileMeta}>
                    {(result.final_score * 100).toFixed(0)}%
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div style={styles.detailRow}>
      <span style={styles.detailLabel}>{label}</span>
      <span style={styles.detailValue}>
        {typeof value === "string" ? value : value}
      </span>
    </div>
  );
}

const styles = {
  sidebar: {
    background: COLORS.bgPanel,
    borderLeft: `1px solid ${COLORS.border}`,
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden",
  },
  empty: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  header: {
    padding: "12px 14px 8px",
    borderBottom: `1px solid ${COLORS.border}`,
  },
  headerTop: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  headerName: {
    fontSize: 14,
    fontWeight: 600,
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: COLORS.textMuted,
    fontSize: 14,
    cursor: "pointer",
    padding: "2px 6px",
    borderRadius: 4,
    flexShrink: 0,
  },
  breadcrumb: {
    marginTop: 4,
    fontSize: 11,
  },
  contentArea: {
    flex: 1,
    overflowY: "auto",
    overflowX: "hidden",
  },
  section: {
    padding: "10px 14px",
    borderBottom: `1px solid ${COLORS.borderSubtle}`,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: 600,
    color: COLORS.textMuted,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    marginBottom: 8,
  },
  codeBlock: {
      keywordWrap: {
        marginTop: 10,
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
      },
      keyword: {
        fontSize: 10,
        color: COLORS.textDim,
        background: COLORS.bgActive,
        border: `1px solid ${COLORS.border}`,
        padding: "4px 6px",
        borderRadius: 999,
      },
    background: COLORS.bgInput,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 6,
    padding: "10px 12px",
    fontSize: 11,
    lineHeight: 1.6,
    color: COLORS.text,
    fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
    overflowX: "auto",
    whiteSpace: "pre",
    maxHeight: 300,
    margin: 0,
  },
  searchError: {
    color: COLORS.accentRed,
    fontSize: 11,
    marginBottom: 8,
  },
  noPreview: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: "20px 0",
  },
  fileRow: {
    display: "flex",
    alignItems: "center",
    padding: "6px 8px",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    transition: "background 0.1s",
  },
  fileMeta: {
    fontSize: 10,
    color: COLORS.textMuted,
  },
  detailGrid: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  detailRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 12,
  },
  detailLabel: {
    color: COLORS.textMuted,
    minWidth: 80,
    fontSize: 11,
  },
  detailValue: {
    color: COLORS.text,
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  importanceBar: {
    flex: 1,
    height: 6,
    background: COLORS.bgInput,
    borderRadius: 3,
    position: "relative",
    overflow: "hidden",
    display: "flex",
    alignItems: "center",
  },
  importanceFill: {
    height: "100%",
    borderRadius: 3,
    transition: "width 0.3s",
  },
  importanceText: {
    position: "absolute",
    right: 0,
    fontSize: 10,
    color: COLORS.textDim,
    paddingRight: 4,
  },
  relatedRow: {
    display: "flex",
    alignItems: "center",
    padding: "5px 8px",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    transition: "background 0.1s",
    color: COLORS.textDim,
  },
  crossBadge: {
    fontSize: 9,
    color: COLORS.accentPurple,
    background: `${COLORS.accentPurple}15`,
    padding: "1px 6px",
    borderRadius: 8,
    border: `1px solid ${COLORS.accentPurple}33`,
  },
};
