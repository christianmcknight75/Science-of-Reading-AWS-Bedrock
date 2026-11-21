// Feature flags. Both are OFF until the sponsor confirms (CLAUDE.md: Behavior is outside
// science-of-reading scope; Progress numbers may count as assessment data).
export const flags = {
  behavior: import.meta.env.VITE_FLAG_BEHAVIOR === "true",
  progress: import.meta.env.VITE_FLAG_PROGRESS === "true",
};
