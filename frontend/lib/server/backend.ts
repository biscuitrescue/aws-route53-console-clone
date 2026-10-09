import "server-only";

/**
 * Where server components reach FastAPI directly. The same variable configures the
 * `/api` proxy at build time (next.config.ts); here it is read when the server runs.
 */
export const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
