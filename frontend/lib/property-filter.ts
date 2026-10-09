import type { PropertyFilterProps } from "@cloudscape-design/components/property-filter";

import type { FilterClause, FilterOperator } from "@/lib/api/params";

/** Property filter operators and the API operators they stand for. */
const OPERATORS: Record<string, FilterOperator> = {
  "=": "eq",
  "!=": "ne",
  ":": "contains",
  "!:": "not_contains",
  "^": "starts_with",
  "!^": "not_starts_with",
  ">": "gt",
  ">=": "gte",
  "<": "lt",
  "<=": "lte",
};

/**
 * The console gives each property a single operator, so choosing a property goes straight
 * to typing its value: text properties match by "contains", choices by "equals". Numeric
 * properties also offer comparisons.
 */
export const CONTAINS_ONLY: PropertyFilterProps.ComparisonOperator[] = [":"];
export const EQUALS_ONLY: PropertyFilterProps.ComparisonOperator[] = ["="];
export const NUMBER_OPERATORS: PropertyFilterProps.ComparisonOperator[] = [
  "=",
  "!=",
  ">",
  ">=",
  "<",
  "<=",
];

export const EMPTY_QUERY: PropertyFilterProps.Query = { tokens: [], operation: "and" };

/** Field the API uses for free-text tokens, which match across the main columns. */
const FREE_TEXT_FIELD = "any";

interface ApiFilters {
  filters: FilterClause[];
  filterMode: "and" | "or";
}

/**
 * Translate a property filter query into API filter clauses. `mapValue` converts a
 * displayed value (such as "Public") into the value the API stores.
 */
export function toApiFilters(
  query: PropertyFilterProps.Query,
  mapValue: (field: string, value: string) => string = (_field, value) => value,
): ApiFilters {
  const filters = query.tokens.flatMap((token): FilterClause[] => {
    const operator = OPERATORS[token.operator];
    const value = String(token.value ?? "").trim();
    if (!operator || !value) return [];
    const field = token.propertyKey ?? FREE_TEXT_FIELD;
    return [{ field, operator, value: mapValue(field, value) }];
  });
  return { filters, filterMode: query.operation };
}

/** "1 match" / "n matches", shown next to the filter while tokens are applied. */
export function matchesText(count: number): string {
  return count === 1 ? "1 match" : `${count} matches`;
}
