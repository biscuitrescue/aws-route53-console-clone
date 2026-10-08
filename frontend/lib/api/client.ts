import createClient from "openapi-fetch";

import { toApiError } from "./errors";
import type { paths } from "./schema";

/** Typed client for the backend. Calls go to this origin and are proxied to FastAPI. */
export const api = createClient<paths>({ baseUrl: "/", credentials: "same-origin" });

interface FetchResult<Data> {
  data?: Data;
  error?: unknown;
  response: Response;
}

/**
 * Unwrap an openapi-fetch result: return the data or throw an `ApiError`.
 * Lets TanStack Query treat API failures as rejected promises.
 */
export async function unwrap<Data>(request: Promise<FetchResult<Data>>): Promise<Data> {
  const { data, error, response } = await request;
  if (!response.ok) {
    throw toApiError(response.status, error);
  }
  return data as Data;
}
