"use client";

import { applyMode, Mode } from "@cloudscape-design/global-styles";
import { useEffect } from "react";

import { usePersistedState } from "./use-persisted-state";

export type VisualMode = "auto" | "light" | "dark";

export const VISUAL_MODE_KEY = "visualMode";
const DARK_QUERY = "(prefers-color-scheme: dark)";

/** The console's visual mode: follow the browser, or force light or dark. */
export function useVisualMode() {
  return usePersistedState<VisualMode>(VISUAL_MODE_KEY, "auto");
}

/** Keeps Cloudscape's colour mode in step with the stored visual mode and the browser. */
export function useApplyVisualMode() {
  const [mode] = useVisualMode();

  useEffect(() => {
    const media = window.matchMedia(DARK_QUERY);
    const apply = () => {
      const dark = mode === "dark" || (mode === "auto" && media.matches);
      applyMode(dark ? Mode.Dark : Mode.Light);
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [mode]);
}

/**
 * Runs before the first paint so a dark-mode visitor never sees a light flash. It mirrors
 * `useApplyVisualMode` and must stay dependency-free: it is inlined into the document.
 */
export const visualModeBootScript = `(function(){try{var m=JSON.parse(localStorage.getItem("r53clone.${VISUAL_MODE_KEY}")||'"auto"');if(m==="dark"||(m==="auto"&&matchMedia("${DARK_QUERY}").matches)){document.body.classList.add("awsui-dark-mode")}}catch(e){}})()`;
