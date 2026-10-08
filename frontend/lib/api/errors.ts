import type { components } from "./schema";

export type ErrorDetail = components["schemas"]["ErrorDetail"];
type ErrorBody = components["schemas"]["ErrorResponse"];

/** A failed API call, carrying the backend's `{code, message, details}` body. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorDetail[];

  constructor(status: number, body: ErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? [];
  }

  /** The message attached to one request field, for inline form errors. */
  fieldMessage(field: string): string | undefined {
    return this.details.find((detail) => detail.field === field)?.message;
  }
}

const UNREACHABLE: ErrorBody = {
  code: "ServiceUnavailable",
  message: "The service is temporarily unavailable. Try again.",
  details: [],
};

function isErrorBody(value: unknown): value is ErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as ErrorBody).code === "string" &&
    typeof (value as ErrorBody).message === "string"
  );
}

/** Build an `ApiError` from whatever a failed response carried. */
export function toApiError(status: number, body: unknown): ApiError {
  return new ApiError(status, isErrorBody(body) ? body : UNREACHABLE);
}
