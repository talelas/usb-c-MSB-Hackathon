import { useState, useRef, useEffect } from "react";
import { COLORS } from "../data/theme";
import { sendChatMessage, getConversationHistory, clearConversation } from "../data/api";

export default function ChatPanel({ sessionId = "default", onClose, width = 400 }) {
  console.log('[ChatPanel] Component mounted with sessionId:', sessionId);
  
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Load conversation history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        console.log('[ChatPanel] Loading conversation history for session:', sessionId);
        const response = await getConversationHistory(sessionId);
        console.log('[ChatPanel] History response:', response);
        if (response.messages && response.messages.length > 0) {
          setMessages(response.messages);
          console.log('[ChatPanel] Loaded', response.messages.length, 'messages from history');
        } else {
          console.log('[ChatPanel] No previous messages found');
        }
      } catch (err) {
        console.error("[ChatPanel] Failed to load conversation history:", err);
      }
    };
    loadHistory();
  }, [sessionId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;

    console.log('[ChatPanel] Sending message:', query);
    console.log('[ChatPanel] Session ID:', sessionId);

    // Add user message
    const userMessage = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      console.log('[ChatPanel] Calling sendChatMessage API...');
      const response = await sendChatMessage(query, sessionId, {
        topK: 10,
        temperature: 0.5,
      });

      console.log('[ChatPanel] Received response:', response);

      // Add assistant response
      const assistantMessage = {
        role: "assistant",
        content: response.answer,
        sources: response.sources || [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
      console.log('[ChatPanel] Assistant message added to UI');
    } catch (err) {
      console.error('[ChatPanel] Error occurred:', err);
      setError(err.message || "Failed to get response");
      // Remove user message on error
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = async () => {
    if (!confirm("Clear conversation history?")) return;
    try {
      await clearConversation(sessionId);
      setMessages([]);
    } catch (err) {
      console.error("Failed to clear conversation:", err);
    }
  };

  return (
    <div style={{ ...styles.panel, width }}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerIcon}>💬</span>
        <span style={styles.headerTitle}>AI Chat</span>
        <button style={styles.clearBtn} onClick={handleClear} title="Clear conversation">
          🗑️
        </button>
        <button style={styles.closeBtn} onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            <span style={{ fontSize: 36, opacity: 0.4 }}>💭</span>
            <span style={{ color: COLORS.textMuted, fontSize: 13 }}>
              Ask questions about your documents
            </span>
            <span style={{ color: COLORS.textFaint, fontSize: 11 }}>
              Try: "What are the main topics?" or "Summarize neural networks"
            </span>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={styles.messageWrapper}>
            <div
              style={{
                ...styles.message,
                ...(msg.role === "user" ? styles.userMessage : styles.assistantMessage),
              }}
            >
              <div style={styles.messageRole}>
                {msg.role === "user" ? "You" : "AI"}
              </div>
              <div style={styles.messageContent}>{msg.content}</div>

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div style={styles.sources}>
                  <div style={styles.sourcesLabel}>Sources:</div>
                  {msg.sources.map((source, idx) => (
                    <div key={idx} style={styles.source}>
                      <span style={styles.sourceIcon}>📄</span>
                      <span style={styles.sourceName}>
                        {source.file_name || `Document ${source.doc_id}`}
                      </span>
                      <span style={styles.sourceScore}>
                        {(source.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={styles.messageWrapper}>
            <div style={{ ...styles.message, ...styles.assistantMessage }}>
              <div style={styles.messageRole}>AI</div>
              <div style={styles.loadingIndicator}>
                <span style={styles.dot}>●</span>
                <span style={styles.dot}>●</span>
                <span style={styles.dot}>●</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div style={styles.error}>
            <span style={{ marginRight: 6 }}>⚠️</span>
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={styles.inputArea}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question... (Enter to send, Shift+Enter for new line)"
          style={styles.input}
          rows={3}
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          style={{
            ...styles.sendBtn,
            opacity: !input.trim() || loading ? 0.5 : 1,
            cursor: !input.trim() || loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
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
  clearBtn: {
    background: "none",
    border: "none",
    color: COLORS.textMuted,
    fontSize: 14,
    cursor: "pointer",
    padding: "2px 6px",
    borderRadius: 4,
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
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "12px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    height: "100%",
  },
  messageWrapper: {
    display: "flex",
    flexDirection: "column",
  },
  message: {
    padding: "10px 12px",
    borderRadius: 10,
    maxWidth: "85%",
  },
  userMessage: {
    alignSelf: "flex-end",
    background: COLORS.accent + "22",
    border: `1px solid ${COLORS.accent}44`,
  },
  assistantMessage: {
    alignSelf: "flex-start",
    background: COLORS.bgActive,
    border: `1px solid ${COLORS.border}`,
  },
  messageRole: {
    fontSize: 10,
    fontWeight: 600,
    color: COLORS.textMuted,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: 6,
  },
  messageContent: {
    fontSize: 13,
    lineHeight: 1.6,
    color: COLORS.text,
    whiteSpace: "pre-wrap",
  },
  sources: {
    marginTop: 10,
    paddingTop: 10,
    borderTop: `1px solid ${COLORS.borderSubtle}`,
  },
  sourcesLabel: {
    fontSize: 10,
    fontWeight: 600,
    color: COLORS.textMuted,
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  source: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: 11,
    color: COLORS.textDim,
    padding: "4px 0",
  },
  sourceIcon: {
    fontSize: 11,
  },
  sourceName: {
    flex: 1,
  },
  sourceScore: {
    fontSize: 10,
    color: COLORS.textMuted,
  },
  loadingIndicator: {
    display: "flex",
    gap: 6,
    alignItems: "center",
  },
  dot: {
    fontSize: 12,
    color: COLORS.accent,
    animation: "pulse 1.5s ease-in-out infinite",
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
  inputArea: {
    padding: "12px",
    borderTop: `1px solid ${COLORS.border}`,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  input: {
    background: COLORS.bgInput,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 8,
    padding: "10px 12px",
    color: COLORS.text,
    fontSize: 13,
    fontFamily: "inherit",
    resize: "none",
    outline: "none",
    transition: "border-color 0.2s",
  },
  sendBtn: {
    background: COLORS.accent,
    color: COLORS.bg,
    border: "none",
    borderRadius: 6,
    padding: "10px 16px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    transition: "opacity 0.2s, transform 0.1s",
  },
};
