import type { RecordType, ZoneType } from "./types";

export type FilterOperator =
  | "eq"
  | "ne"
  | "contains"
  | "not_contains"
  | "starts_with"
  | "not_starts_with"
  | "gt"
  | "gte"
  | "lt"
  | "lte";

/** One property filter, sent to the API as `field:operator:value`. */
export interface FilterClause {
  field: string;
  operator: FilterOperator;
  value: string;
}

interface ListParams {
  search?: string;
  filters?: FilterClause[];
  filterMode?: "and" | "or";
  sort?: string;
  order?: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface ZoneListParams extends ListParams {
  type?: ZoneType;
}

export interface RecordListParams extends ListParams {
  types?: RecordType[];
}

/** Translate list parameters into the query string the API expects. */
export function toListQuery(params: ListParams) {
  return {
    search: params.search || undefined,
    filter: params.filters?.map(({ field, operator, value }) => `${field}:${operator}:${value}`),
    filter_mode: params.filterMode,
    sort: params.sort,
    order: params.order,
    page: params.page,
    page_size: params.pageSize,
  };
}
