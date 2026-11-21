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
        control: "var(--color-control-border)",
        idea: "var(--color-idea)",
        primary: { DEFAULT: "var(--color-primary)", hover: "var(--color-primary-hover)" },
        highlight: "var(--color-highlight)",
        warm: "var(--color-warm)",
        "warm-2": "var(--color-warm-2)",
        tint: "var(--color-tint)",
        "tint-2": "var(--color-tint-2)",
        "notice-bg": "var(--color-notice-bg)",
        "notice-text": "var(--color-notice-text)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        lift: "var(--shadow-lift)",
        float: "var(--shadow-float)",
      },
      fontFamily: { heading: ["var(--font-heading)"], body: ["var(--font-body)"] },
      minHeight: { target: "var(--target-min)", classroom: "var(--target-classroom)" },
      minWidth: { target: "var(--target-min)", classroom: "var(--target-classroom)" },
    },
  },
};
