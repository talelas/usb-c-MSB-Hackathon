import { useState } from "react";
import { COLORS, getExtColor, getExtIcon } from "../data/theme";

export default function TopBar({ openTabs, activeTabId, onTabClick, onTabClose }) {
  return (
    <div style={styles.bar}>
      {/* Logo */}
      <div style={styles.logoArea}>
        <span style={styles.logoIcon}>✦</span>
        <span style={styles.logoText}>Constellation</span>
      </div>

      {/* Tabs */}
      <div style={styles.tabStrip}>
        {openTabs.map((tab) => (
          <div
            key={tab.id}
            style={{
              ...styles.tab,
              ...(tab.id === activeTabId ? styles.tabActive : {}),
            }}
            onClick={() => onTabClick(tab.id)}
          >
            <span style={{ color: getExtColor(tab.ext), marginRight: 5, fontSize: 11 }}>
              {getExtIcon(tab.ext)}
            </span>
            <span style={styles.tabLabel}>{tab.name}</span>
            <span
              style={styles.tabClose}
              onClick={(e) => {
                e.stopPropagation();
                onTabClose(tab.id);
              }}
            >
              ×
            </span>
          </div>
        ))}
      </div>

      {/* Right actions */}
      <div style={styles.actions}>
        <button style={styles.actionBtn} title="Settings">⚙</button>
      </div>
    </div>
  );
}

const styles = {
  bar: {
    height: 40,
    minHeight: 40,
    background: COLORS.bgPanel,
    borderBottom: `1px solid ${COLORS.border}`,
    display: "flex",
    alignItems: "center",
    padding: "0 12px",
    gap: 0,
    zIndex: 20,
  },
  logoArea: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    paddingRight: 16,
    borderRight: `1px solid ${COLORS.border}`,
    marginRight: 4,
    minWidth: 130,
  },
  logoIcon: {
    fontSize: 16,
    color: COLORS.accentCyan,
    filter: `drop-shadow(0 0 4px ${COLORS.accentCyan})`,
  },
  logoText: {
    fontSize: 13,
    fontWeight: 700,
    color: COLORS.textDim,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  tabStrip: {
    display: "flex",
    flex: 1,
    alignItems: "center",
    gap: 2,
    overflow: "hidden",
  },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    padding: "5px 10px",
    borderRadius: "6px 6px 0 0",
    cursor: "pointer",
    background: "transparent",
    color: COLORS.textMuted,
    fontSize: 12,
    whiteSpace: "nowrap",
    transition: "background 0.15s",
    maxWidth: 160,
  },
  tabActive: {
    background: COLORS.bgActive,
    color: COLORS.text,
  },
  tabLabel: {
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  tabClose: {
    marginLeft: 4,
    fontSize: 14,
    lineHeight: 1,
    color: COLORS.textMuted,
    cursor: "pointer",
    borderRadius: 3,
    padding: "0 2px",
  },
  actions: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginLeft: "auto",
  },
  actionBtn: {
    background: "none",
    border: "none",
    color: COLORS.textDim,
    cursor: "pointer",
    fontSize: 15,
    padding: 4,
    borderRadius: 4,
  },
};
