import { useEffect, useRef } from "react";
import type { Comparison } from "./types";
type Tool = {
  name: string;
  description: string;
  inputSchema: object;
  annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
  execute: (input: unknown) => unknown;
};
type Context = {
  registerTool: (
    tool: Tool,
    options: { signal: AbortSignal },
  ) => void | Promise<void>;
};
export function useEvidenceTools(
  data: Comparison | null,
  navigate: (id: string) => void,
) {
  const state = useRef({ data, navigate });
  state.current = { data, navigate };
  useEffect(() => {
    const context = (document as Document & { modelContext?: Context })
      .modelContext;
    if (!context?.registerTool) return;
    const controller = new AbortController();
    const tools: Tool[] = [
      {
        name: "read_disclosure_comparison",
        description:
          "Read the loaded annual comparison. Demo mode contains fictional data.",
        inputSchema: {
          type: "object",
          properties: {},
          additionalProperties: false,
        },
        annotations: { readOnlyHint: true, untrustedContentHint: true },
        execute: () => {
          const d = state.current.data;
          return d
            ? {
                company: d.companyName,
                mode: d.mode,
                id: d.id,
                changes: d.changes.map((c) => ({
                  id: c.id,
                  title: c.title,
                  kind: c.kind,
                })),
                financials: d.financials,
              }
            : { status: "not_available" };
        },
      },
      {
        name: "navigate_disclosure_evidence",
        description:
          "Navigate to evidence for a change in the loaded comparison.",
        inputSchema: {
          type: "object",
          properties: { changeId: { type: "string" } },
          required: ["changeId"],
          additionalProperties: false,
        },
        annotations: { readOnlyHint: false, untrustedContentHint: true },
        execute: async (input) => {
          if (
            !input ||
            typeof input !== "object" ||
            !("changeId" in input) ||
            typeof input.changeId !== "string"
          )
            throw new Error("changeId is required");
          const id = input.changeId,
            d = state.current.data;
          if (!d || ![...d.changes, ...d.financials].some((x) => x.id === id))
            throw new Error("Unknown changeId");
          state.current.navigate(id);
          await new Promise((r) => setTimeout(r, 70));
          return { changeId: id, mode: d.mode, url: location.href };
        },
      },
    ];
    for (const tool of tools) {
      try {
        void Promise.resolve(
          context.registerTool(tool, { signal: controller.signal }),
        ).catch(() => {});
      } catch {
        /* Optional capability. */
      }
    }
    return () => controller.abort();
  }, []);
}
