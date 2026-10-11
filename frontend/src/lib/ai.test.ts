import { describe, expect, it } from "vitest";
import type { Explanation } from "../api/types";
import { aiEnabled, explanationOrigin, type ExplanationMetrics } from "./ai";

const base = { source: "template", fallback_reason: "PROVIDER_NOT_CONFIGURED" } as Explanation;

describe("explanationOrigin", () => {
  it("labels AI-written explanations", () => {
    const origin = explanationOrigin({ ...base, source: "llm", fallback_reason: null });
    expect(origin.badge).toBe("Written by AI");
    expect(origin.retry).toBe(false);
  });
  it("treats a missing provider as switched off, not as a failure", () => {
    const origin = explanationOrigin(base);
    expect(origin.badge).toBe("Standard wording");
    expect(origin.tone).toBe("muted");
  });
  it("offers a retry only for transient provider failures", () => {
    expect(explanationOrigin({ ...base, fallback_reason: "PROVIDER_TIMEOUT" }).retry).toBe(true);
    expect(explanationOrigin({ ...base, fallback_reason: "CLAIMS_REJECTED" }).retry).toBe(false);
    expect(explanationOrigin({ ...base, fallback_reason: "CLAIMS_REJECTED" }).tone).toBe("info");
  });
  it("keeps unknown reasons readable", () => {
    expect(explanationOrigin({ ...base, fallback_reason: "SOMETHING_NEW" }).detail).toContain("something new");
  });
});

describe("aiEnabled", () => {
  it("reads the service's zero offline cost as AI off", () => {
    expect(aiEnabled(undefined)).toBeUndefined();
    expect(aiEnabled({ offline_cost: 0 } as ExplanationMetrics)).toBe(false);
    expect(aiEnabled({ offline_cost: null } as ExplanationMetrics)).toBe(true);
  });
});
