export const WS_BACKEND_URL =
  import.meta.env.VITE_WS_BACKEND_URL || "ws://127.0.0.1:7001";

export const HTTP_BACKEND_URL =
  import.meta.env.VITE_HTTP_BACKEND_URL || "http://127.0.0.1:7001";

// frontend and backend ports are the same
export const BEHIND_SAME_ALB =
  import.meta.env.VITE_BEHIND_SAME_ALB === "true" || false;
