"use client";

import type { PropertyFilterProps } from "@cloudscape-design/components/property-filter";
import { useEffect, useRef } from "react";

/**
 * In the console, choosing a property in the filter goes straight to its values: the
 * input reads `Hosted zone name : `. Stock Cloudscape stops at `Hosted zone name` and lists
 * the operators first. This completes the operator after a property has been chosen with
 * a click or Enter. Typing a property's name is left alone, so it can still be searched
 * for as free text.
 *
 * Attach the returned ref to an element around the property filter.
 */
export function usePropertyOperatorCompletion(
  properties: readonly PropertyFilterProps.FilteringProperty[],
) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = container.current;
    // React tracks the value it last set, so a change must go through the native setter.
    const setInputValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    if (!element || !setInputValue) return;

    const complete = () => {
      const input = element.querySelector("input");
      const property = properties.find((candidate) => candidate.propertyLabel === input?.value);
      if (!input || !property) return;
      const operator = property.defaultOperator ?? property.operators?.[0] ?? ":";
      setInputValue.call(input, `${property.propertyLabel} ${operator} `);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    };
    // The filter updates its input after the event; look once that has happened.
    const afterChoice = (event: Event) => {
      if (event instanceof KeyboardEvent && event.key !== "Enter") return;
      requestAnimationFrame(complete);
    };

    // Options render in a dropdown outside this element when it expands to the viewport,
    // and the dropdown keeps its events to itself, so listen while they are captured.
    document.addEventListener("click", afterChoice, true);
    element.addEventListener("keydown", afterChoice, true);
    return () => {
      document.removeEventListener("click", afterChoice, true);
      element.removeEventListener("keydown", afterChoice, true);
    };
  }, [properties]);

  return container;
}
