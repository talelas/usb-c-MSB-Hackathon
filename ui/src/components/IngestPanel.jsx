import { useState } from "react";
import { COLORS } from "../data/theme";
import { ingestDirectory } from "../data/api";

export default function IngestPanel({ onClose, onIngestComplete, width = 400 }) {
  const [directory, setDirectory] = useState("");
  const [rebuildGraphs, setRebuildGraphs] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleIngest = async () => {
    if (loading) return;

    console.log('[IngestPanel] Starting ingestion:', { directory, rebuildGraphs });
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      console.log('[IngestPanel] Calling ingest API...');
      const response = await ingestDirectory(
        directory.trim() || null,
        rebuildGraphs
      );

      console.log('[IngestPanel] Ingestion response:', response);
      setResult(response);

      if (response.error) {
        setError(response.error);
      } else {
        // Notify parent to reload documents
        setTimeout(() => {
          if (onIngestComplete) {
            onIngestComplete();
          }
        }, 1000);
      }
    } catch (err) {
      console.error('[IngestPanel] Ingestion failed:', err);
      setError(err.message || "Failed to start ingestion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ ...styles.panel, width }}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerIcon}>📥</span>
        <span style={styles.headerTitle}>Ingest Documents</span>
        <button style={styles.closeBtn} onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {/* Directory Input */}
        <div style={styles.section}>
          <label style={styles.label}>
            Directory Path or Drive Link
            <span style={styles.labelHint}>(leave empty for default: data/raw)</span>
          </label>
          <input
            type="text"
            value={directory}
            onChange={(e) => setDirectory(e.target.value)}
            placeholder="/path/to/documents or https://drive.google.com/..."
            style={styles.input}
            disabled={loading}
          />
          <div style={styles.hint}>
            <strong>Local Path:</strong> <code style={styles.code}>C:/Users/User/Documents</code>
            <br />
            <strong>Google Drive:</strong> <code style={styles.code}>https://drive.google.com/drive/folders/...</code>
            <br />
            <strong>OneDrive:</strong> <code style={styles.code}>https://1drv.ms/f/s!...</code>
          </div>
        </div>

        {/* Options */}
        <div style={styles.section}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={rebuildGraphs}
              onChange={(e) => setRebuildGraphs(e.target.checked)}
              disabled={loading}
              style={styles.checkbox}
            />
            <span>Rebuild graphs after ingestion</span>
          </label>
          <div style={styles.hint}>
            This will recreate the knowledge graph from all documents.
            Recommended for best results.
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleIngest}
          disabled={loading}
          style={{
            ...styles.ingestBtn,
            opacity: loading ? 0.6 : 1,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Processing..." : "🚀 Start Ingestion"}
        </button>

        {/* Result Display */}
        {result && !error && (
          <div style={styles.result}>
            <div style={styles.resultTitle}>✅ Ingestion Complete</div>
            <div style={styles.resultGrid}>
              <ResultRow label="Directory" value={result.directory} />
              <ResultRow label="Total Files" value={result.total_files} />
              <ResultRow label="Ingested" value={result.ingested} success />
              {result.failed > 0 && (
                <ResultRow label="Failed" value={result.failed} error />
              )}
              <ResultRow
                label="Graphs Built"
                value={result.graph_built ? "Yes" : "No"}
              />
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div style={styles.error}>
            <span style={{ marginRight: 6 }}>⚠️</span>
            {error}
          </div>
        )}

        {/* Info */}
        <div style={styles.info}>
          <div style={styles.infoTitle}>ℹ️ How it works</div>
          <ul style={styles.infoList}>
            <li>Accepts local directories or cloud drive links</li>
            <li>Downloads files from Google Drive/OneDrive if link provided</li>
            <li>Scans for documents (PDF, TXT, MD, images, audio)</li>
            <li>Extracts text and generates embeddings</li>
            <li>Creates summaries and extracts keywords</li>
            <li>Stores in vector database for semantic search</li>
            <li>Builds knowledge graph for exploration</li>
          </ul>
          <div style={styles.supportedLinks}>
            <div style={styles.supportedTitle}>☁️ Supported cloud links:</div>
            <div style={styles.supportedItem}>
              <span style={styles.supportedIcon}>🟢</span>
              Google Drive (publicly shared folders/files)
            </div>
            <div style={styles.supportedItem}>
              <span style={styles.supportedIcon}>🔵</span>
              OneDrive (publicly shared folders/files)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultRow({ label, value, success, error }) {
  return (
    <div style={styles.resultRow}>
      <span style={styles.resultLabel}>{label}</span>
      <span
        style={{
          ...styles.resultValue,
          color: success
            ? COLORS.accentGreen
            : error
            ? COLORS.accentRed
            : COLORS.text,
        }}
      >
        {value}
      </span>
    </div>
  );
}

const styles = {
  panel: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    background: COLORS.bgPanel,
    borderLeft: `1px solid ${COLORS.border}`,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "12px 14px",
    borderBottom: `1px solid ${COLORS.border}`,
  },
  headerIcon: {
    fontSize: 16,
  },
  headerTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: COLORS.text,
    flex: 1,
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: COLORS.textMuted,
    fontSize: 14,
    cursor: "pointer",
    padding: "2px 6px",
    borderRadius: 4,
  },
  content: {
    flex: 1,
    overflowY: "auto",
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: COLORS.text,
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  labelHint: {
    fontSize: 10,
    fontWeight: 400,
    color: COLORS.textMuted,
  },
  input: {
    background: COLORS.bgInput,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 6,
    padding: "10px 12px",
    color: COLORS.text,
    fontSize: 13,
    fontFamily: "'Fira Code', 'Cascadia Code', monospace",
    outline: "none",
    transition: "border-color 0.2s",
  },
  hint: {
    fontSize: 11,
    color: COLORS.textMuted,
    lineHeight: 1.5,
  },
  code: {
    background: COLORS.bgActive,
    padding: "2px 6px",
    borderRadius: 3,
    fontSize: 10,
    fontFamily: "monospace",
  },
  checkboxLabel: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 13,
    color: COLORS.text,
    cursor: "pointer",
  },
  checkbox: {
    cursor: "pointer",
  },
  ingestBtn: {
    background: COLORS.accentGreen,
    color: COLORS.bg,
    border: "none",
    borderRadius: 8,
    padding: "12px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    transition: "opacity 0.2s, transform 0.1s",
    marginTop: 8,
  },
  result: {
    background: `${COLORS.accentGreen}15`,
    border: `1px solid ${COLORS.accentGreen}33`,
    borderRadius: 8,
    padding: "12px",
  },
  resultTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: COLORS.accentGreen,
    marginBottom: 10,
  },
  resultGrid: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  resultRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 12,
  },
  resultLabel: {
    color: COLORS.textMuted,
  },
  resultValue: {
    color: COLORS.text,
    fontWeight: 500,
  },
  error: {
    padding: "10px 12px",
    background: `${COLORS.accentRed}15`,
    border: `1px solid ${COLORS.accentRed}44`,
    borderRadius: 8,
    color: COLORS.accentRed,
    fontSize: 12,
    display: "flex",
    alignItems: "center",
  },
  info: {
    background: `${COLORS.accent}08`,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 8,
    padding: "12px",
    marginTop: "auto",
  },
  infoTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: COLORS.textDim,
    marginBottom: 8,
  },
  infoList: {
    margin: 0,
    paddingLeft: 20,
    fontSize: 11,
    color: COLORS.textMuted,
    lineHeight: 1.6,
  },
  supportedLinks: {
    marginTop: 12,
    paddingTop: 12,
    borderTop: `1px solid ${COLORS.borderSubtle}`,
  },
  supportedTitle: {
    fontSize: 10,
    fontWeight: 600,
    color: COLORS.textDim,
    marginBottom: 6,
  },
  supportedItem: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 10,
    color: COLORS.textMuted,
    marginBottom: 4,
  },
  supportedIcon: {
    fontSize: 8,
  },
};
