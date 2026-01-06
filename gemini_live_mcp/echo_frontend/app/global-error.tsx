"use client";

// Minimal global error boundary that doesn't use any React context or hooks
// This prevents the "useContext is null" error during Next.js 16 prerendering
export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <html lang="en">
            <body
                style={{
                    margin: 0,
                    padding: 0,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    minHeight: "100vh",
                    fontFamily: "system-ui, -apple-system, sans-serif",
                    backgroundColor: "#0a0a0a",
                    color: "#ffffff",
                }}
            >
                <h2>Something went wrong!</h2>
                <button
                    onClick={reset}
                    style={{
                        marginTop: "1rem",
                        padding: "0.75rem 1.5rem",
                        backgroundColor: "#3b82f6",
                        color: "white",
                        border: "none",
                        borderRadius: "0.5rem",
                        cursor: "pointer",
                        fontSize: "1rem",
                    }}
                >
                    Try again
                </button>
            </body>
        </html>
    );
}
