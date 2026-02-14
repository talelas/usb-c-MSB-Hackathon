import { COLORS } from "../data/theme";

export default function StatusBar({ nodeCount, linkCount, selectedNode, zoom }) {
  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <span style={styles.item}>
          <span style={styles.dot} />
          {nodeCount} nodes
        </span>
        <span style={styles.sep}>·</span>
        <span style={styles.item}>{linkCount} links</span>
      </div>

      <div style={styles.center}>
        {selectedNode && (
          <span style={{ ...styles.item, color: COLORS.accentCyan }}>
            ◆ {selectedNode.name}
          </span>
        )}
      </div>

      <div style={styles.right}>
        <span style={styles.item}>Zoom: {(zoom * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}

const styles = {
  bar: {
    height: 24,
    minHeight: 24,
    background: COLORS.bgPanel,
    borderTop: `1px solid ${COLORS.border}`,
    display: "flex",
    alignItems: "center",
    padding: "0 12px",
    fontSize: 11,
    color: COLORS.textMuted,
    fontFamily: "'Inter', 'SF Pro', sans-serif",
    zIndex: 20,
  },
  left: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    flex: 1,
  },
  center: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
  },
  right: {
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    flex: 1,
    gap: 12,
  },
  item: {
    display: "flex",
    alignItems: "center",
    gap: 4,
  },
  sep: {
    color: COLORS.textFaint,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: COLORS.accentGreen,
    boxShadow: `0 0 4px ${COLORS.accentGreen}`,
  },
};
