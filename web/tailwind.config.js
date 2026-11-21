/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        border: "var(--color-border)",
        primary: { DEFAULT: "var(--color-primary)", hover: "var(--color-primary-hover)" },
        highlight: "var(--color-highlight)",
        "notice-bg": "var(--color-notice-bg)",
        "notice-text": "var(--color-notice-text)",
      },
      fontFamily: { heading: ["var(--font-heading)"], body: ["var(--font-body)"] },
      minHeight: { target: "var(--target-min)", classroom: "var(--target-classroom)" },
      minWidth: { target: "var(--target-min)", classroom: "var(--target-classroom)" },
    },
  },
};
