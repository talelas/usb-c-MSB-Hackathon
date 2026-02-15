import { useState, useEffect, useRef, useMemo } from "react";
import { COLORS, getExtColor, getExtIcon } from "../data/theme";

export default function SearchBar({ onSelectNode, onSearch, graphNodes = [] }) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef(null);

  // Ctrl+K / Cmd+K to focus
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === "Escape") {
        inputRef.current?.blur();
        setIsFocused(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Local fuzzy filter for autocomplete
  const suggestions = useMemo(() => {
    if (!query.trim()) return [];
    const lc = query.toLowerCase();
    return graphNodes
      .filter(
        (n) =>
          n.name.toLowerCase().includes(lc) ||
          n.group.toLowerCase().includes(lc) ||
          n.ext.toLowerCase().includes(lc)
      )
      .slice(0, 8);
  }, [query]);

  // Reset selection on suggestion change
  useEffect(() => {
    setSelectedIdx(0);
  }, [suggestions.length]);

  const handleKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (suggestions.length > 0 && suggestions[selectedIdx]) {
        onSelectNode(suggestions[selectedIdx]);
        setQuery("");
        setIsFocused(false);
        inputRef.current?.blur();
      } else if (query.trim()) {
        // Semantic search — pass to backend
        onSearch?.(query.trim());
      }
    }
  };

  const showDropdown = isFocused && query.trim().length > 0;

  return (
    <div style={styles.wrapper}>
      <div
        style={{
          ...styles.bar,
          borderColor: isFocused ? COLORS.borderFocus : COLORS.border,
          boxShadow: isFocused
            ? `0 0 20px ${COLORS.accent}22, 0 4px 24px #00000066`
            : "0 4px 24px #00000044",
        }}
      >
        <span style={styles.icon}>🔍</span>
        <input
          ref={inputRef}
          type="text"
          placeholder='Search files or ask "which file has feature X?"   (Ctrl+K)'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          onKeyDown={handleKeyDown}
          style={styles.input}
        />
        {query && (
          <span
            style={styles.clearBtn}
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
          >
            ✕
          </span>
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && suggestions.length > 0 && (
        <div style={styles.dropdown}>
          {suggestions.map((node, i) => (
            <div
              key={node.id}
              style={{
                ...styles.suggestion,
                background:
                  i === selectedIdx ? COLORS.bgActive : "transparent",
              }}
              onMouseEnter={() => setSelectedIdx(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                onSelectNode(node);
                setQuery("");
                setIsFocused(false);
              }}
            >
              <span style={{ marginRight: 6, fontSize: 13 }}>
                {getExtIcon(node.ext)}
              </span>
              <span style={{ color: getExtColor(node.ext), fontWeight: 500 }}>
                {node.name}
              </span>
              <span style={styles.suggestionMeta}>
                {node.group} · {(node.importance * 100).toFixed(0)}%
              </span>
            </div>
          ))}
          {query.length > 2 && (
            <div
              style={{
                ...styles.suggestion,
                borderTop: `1px solid ${COLORS.border}`,
                color: COLORS.accent,
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                onSearch?.(query.trim());
              }}
            >
              <span style={{ marginRight: 6 }}>🧠</span>
              Semantic search: "{query}"
              <span style={styles.suggestionMeta}>Enter ↵</span>
            </div>
          )}
        </div>
      )}

      {showDropdown && suggestions.length === 0 && query.length > 1 && (
        <div style={styles.dropdown}>
          <div
            style={{ ...styles.suggestion, color: COLORS.accent }}
            onMouseDown={(e) => {
              e.preventDefault();
              onSearch?.(query.trim());
            }}
          >
            <span style={{ marginRight: 6 }}>🧠</span>
            Semantic search: "{query}"
            <span style={styles.suggestionMeta}>Enter ↵</span>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    position: "absolute",
    bottom: 24,
    left: "50%",
    transform: "translateX(-50%)",
    width: "min(700px, 85%)",
    zIndex: 15,
  },
  bar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    background: `${COLORS.bgPanel}ee`,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 14,
    padding: "14px 20px",
    backdropFilter: "blur(16px)",
    transition: "border-color 0.2s, box-shadow 0.2s",
  },
  icon: {
    fontSize: 18,
    flexShrink: 0,
    opacity: 0.6,
  },
  input: {
    flex: 1,
    background: "none",
    border: "none",
    outline: "none",
    color: COLORS.text,
    fontSize: 15,
    fontFamily: "'Inter', 'SF Pro', sans-serif",
  },
  clearBtn: {
    color: COLORS.textMuted,
    cursor: "pointer",
    fontSize: 14,
    padding: "4px 6px",
    borderRadius: 4,
    flexShrink: 0,
  },
  dropdown: {
    marginTop: 4,
    background: `${COLORS.bgPanel}f5`,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 10,
    overflow: "hidden",
    backdropFilter: "blur(16px)",
    boxShadow: "0 8px 32px #00000066",
  },
  suggestion: {
    display: "flex",
    alignItems: "center",
    padding: "10px 20px",
    cursor: "pointer",
    fontSize: 14,
    color: COLORS.text,
    transition: "background 0.1s",
  },
  suggestionMeta: {
    marginLeft: "auto",
    fontSize: 11,
    color: COLORS.textMuted,
    paddingLeft: 12,
  },
};
