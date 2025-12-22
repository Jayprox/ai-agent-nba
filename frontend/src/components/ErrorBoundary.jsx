// frontend/src/components/ErrorBoundary.jsx
import React from "react";

/**
 * ErrorBoundary
 * - Catches render/runtime errors in child component trees (including hook/runtime crashes)
 * - Shows a dark-themed fallback panel instead of a blank page
 * - Provides "Try again" (reset) and "Reload page" actions
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      lastErrorAt: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
      lastErrorAt: new Date().toISOString(),
    };
  }

  componentDidCatch(error, errorInfo) {
    // Keep this console log: it's the fastest way to debug locally.
    // You can later wire this to Sentry/Datadog/etc.
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] Caught error:", error, errorInfo);

    this.setState({ errorInfo });
  }

  reset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      lastErrorAt: null,
    });

    if (typeof this.props.onReset === "function") {
      this.props.onReset();
    }
  };

  reload = () => {
    window.location.reload();
  };

  copyDetails = async () => {
    try {
      const { error, errorInfo, lastErrorAt } = this.state;

      const message = [
        `Captured At: ${lastErrorAt || "—"}`,
        "",
        "Error:",
        error?.stack || String(error),
        "",
        "Component Stack:",
        errorInfo?.componentStack || "—",
      ].join("\n");

      await navigator.clipboard.writeText(message);
      // eslint-disable-next-line no-console
      console.log("[ErrorBoundary] Error details copied to clipboard.");
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[ErrorBoundary] Failed to copy error details:", e);
    }
  };

  render() {
    const { hasError, error, errorInfo, lastErrorAt } = this.state;

    if (!hasError) return this.props.children;

    const title = this.props.title || "Something went wrong";
    const subtitle =
      this.props.subtitle ||
      "The page encountered an unexpected error. You can try again or reload the page.";

    const errorText = error?.stack || String(error || "Unknown error");
    const componentStack = errorInfo?.componentStack || "";

    return (
      <div
        style={{
          minHeight: "100vh",
          padding: 24,
          background: "linear-gradient(180deg, #050b18, #020617)",
          color: "#e5e7eb",
        }}
      >
        <div
          style={{
            maxWidth: 980,
            margin: "0 auto",
            borderRadius: 16,
            border: "1px solid #334155",
            background: "rgba(17,24,39,0.70)",
            padding: 18,
            boxShadow: "0 12px 30px rgba(0,0,0,0.35)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 900, marginBottom: 6 }}>{title}</div>
              <div style={{ fontSize: 13, color: "#9ca3af" }}>{subtitle}</div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 10 }}>
                Captured: <span style={{ color: "#e5e7eb", fontWeight: 800 }}>{lastErrorAt || "—"}</span>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <button
                onClick={this.reset}
                style={{
                  padding: "10px 12px",
                  borderRadius: 10,
                  fontWeight: 800,
                  border: "1px solid #334155",
                  background: "#0b1220",
                  color: "#e5e7eb",
                  cursor: "pointer",
                }}
                title="Reset the UI state and try rendering again"
              >
                Try again
              </button>

              <button
                onClick={this.reload}
                style={{
                  padding: "10px 12px",
                  borderRadius: 10,
                  fontWeight: 800,
                  border: "1px solid #334155",
                  background: "#2563eb",
                  color: "white",
                  cursor: "pointer",
                }}
                title="Reload the page"
              >
                Reload page
              </button>

              <button
                onClick={this.copyDetails}
                style={{
                  padding: "10px 12px",
                  borderRadius: 10,
                  fontWeight: 800,
                  border: "1px solid #334155",
                  background: "transparent",
                  color: "#e5e7eb",
                  cursor: "pointer",
                }}
                title="Copy error + component stack to clipboard"
              >
                Copy details
              </button>
            </div>
          </div>

          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            <div
              style={{
                borderRadius: 12,
                border: "1px solid #334155",
                background: "rgba(0,0,0,0.20)",
                padding: 12,
              }}
            >
              <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6, fontWeight: 800 }}>
                Error
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 12,
                  lineHeight: 1.4,
                  color: "#e5e7eb",
                }}
              >
                {errorText}
              </pre>
            </div>

            {componentStack ? (
              <div
                style={{
                  borderRadius: 12,
                  border: "1px solid #334155",
                  background: "rgba(0,0,0,0.18)",
                  padding: 12,
                }}
              >
                <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6, fontWeight: 800 }}>
                  Component Stack
                </div>
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontSize: 12,
                    lineHeight: 1.4,
                    color: "#cbd5e1",
                  }}
                >
                  {componentStack}
                </pre>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
