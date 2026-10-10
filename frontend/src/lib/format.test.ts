import { describe, expect, it } from "vitest";
import { niceTicks } from "../components/charts/common";
import { humanize, impactAvailable, impactLabel, percentage, percentValue, periodLabel, prettyUnit, toNumber } from "./format";

describe("toNumber", () => {
  it("parses Pydantic decimal strings and rejects booleans and non-finite values", () => {
    expect(toNumber("553.19400")).toBe(553.194);
    expect(toNumber(0)).toBe(0);
    expect(toNumber(true)).toBeNull();
    expect(toNumber("NaN")).toBeNull();
    expect(toNumber("Infinity")).toBeNull();
    expect(toNumber("")).toBeNull();
    expect(toNumber(null)).toBeNull();
  });
});

describe("percentage", () => {
  it("formats probabilities and refuses values outside 0..1", () => {
    expect(percentage("0.10683173034858034")).toBe("10.7%");
    expect(percentage(0)).toBe("0.0%");
    expect(percentage("1.2")).toBe("Not available");
    expect(percentage(-0.1)).toBe("Not available");
    expect(percentValue(undefined)).toBeNull();
  });
});

describe("impact labels", () => {
  const base = { units: "kg CO2e/year" };
  it("never shows unavailable impact as zero", () => {
    expect(impactLabel({ ...base, status: "UNAVAILABLE", value: null })).toBe("Not available");
    expect(impactLabel({ ...base, status: "UNAVAILABLE", value: "0" })).toBe("Not available");
    expect(impactAvailable({ status: "AVAILABLE", value: null })).toBe(false);
  });
  it("preserves zero and negative available impact", () => {
    expect(impactLabel({ ...base, status: "AVAILABLE", value: "0" })).toBe("0 kg CO₂e/yr");
    expect(impactLabel({ ...base, status: "AVAILABLE", value: "-12.34" })).toBe("-12.3 kg CO₂e/yr");
    expect(impactLabel({ ...base, status: "AVAILABLE", value: "2063.6143200" })).toBe("2,063.6 kg CO₂e/yr");
  });
});

describe("text helpers", () => {
  it("keeps units and acronyms readable", () => {
    expect(prettyUnit("kg CO2/year")).toBe("kg CO₂/yr");
    expect(humanize("vehicle_fuel_combustion_and_charging_generation_co2")).toBe("Vehicle fuel combustion and charging generation CO₂");
    expect(humanize("MASS_AFFLUENT")).toBe("Mass affluent");
    expect(humanize("auc_range")).toBe("AUC range");
  });
  it("reads Python dict-repr periods from aggregate groups", () => {
    expect(periodLabel("{'start': '2026-06-30', 'end': '2027-06-30'}")).toBe("30 Jun 2026 to 30 Jun 2027");
    expect(periodLabel({ start: "2025-01-01", end: "2026-01-01" })).toBe("1 Jan 2025 to 1 Jan 2026");
  });
});

describe("niceTicks", () => {
  it("covers the maximum with clean steps", () => {
    expect(niceTicks(24)).toEqual([0, 10, 20, 30]);
    expect(niceTicks(1, 4, true)).toEqual([0, 1]);
    expect(niceTicks(0)).toEqual([0, 1]);
  });
});
