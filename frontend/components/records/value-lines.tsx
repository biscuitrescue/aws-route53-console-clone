import type { CSSProperties } from "react";

const LINE: CSSProperties = { overflow: "hidden", textOverflow: "ellipsis" };

/** A record's values, one per line; each line truncates with an ellipsis unless lines wrap. */
export function ValueLines({ values }: { values: readonly string[] }) {
  return values.map((value) => (
    <div key={value} style={LINE} title={value}>
      {value}
    </div>
  ));
}
