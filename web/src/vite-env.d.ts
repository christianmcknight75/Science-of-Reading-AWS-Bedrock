/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_API_MODE?: "mock" | "real";
  readonly VITE_FLAG_BEHAVIOR?: string;
  readonly VITE_FLAG_PROGRESS?: string;
  readonly VITE_CONTENT_LAST_UPDATED?: string;
}
