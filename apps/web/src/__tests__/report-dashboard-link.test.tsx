import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { NeighborhoodReport } from "@/types/api";

const authMock = vi.fn();

vi.mock("@/lib/auth", () => ({
  auth: (...args: unknown[]) => authMock(...args),
}));

vi.mock("@/components/layout/Header", () => ({
  default: () => <header data-testid="header">Header</header>,
}));

vi.mock("@/components/layout/Footer", () => ({
  default: () => <footer data-testid="footer">Footer</footer>,
}));

vi.mock("@/components/report/MapView", () => ({
  default: () => <div data-testid="map">Map</div>,
}));

vi.mock("@/components/report/ScoreSummary", () => ({
  default: () => <div>Score summary</div>,
}));

vi.mock("@/components/report/ScoreBreakdown", () => ({
  default: () => <div>Score breakdown</div>,
}));

vi.mock("@/components/report/ReportAiSummary", () => ({
  default: () => <div>AI summary</div>,
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api";
import ReportPage from "@/app/report/[addressId]/page";

const mockReport = {
  address: "123 Main St",
  address_normalized: "123 Main St, Austin, TX 78701",
  geoid: "48453001100",
  latitude: 30.2672,
  longitude: -97.7431,
  overall_score: 82,
  healthcare: { score: 87, label: "Healthcare", summary: "", factors: [] },
  safety: { score: 74, label: "Safety", summary: "", factors: [] },
  environment: { score: 74, label: "Environment", summary: "", factors: [] },
  education: { score: 91, label: "Schools", summary: "", factors: [] },
  economic: { score: 68, label: "Economy", summary: "", factors: [] },
  narrative: "Test narrative",
  data_vintage: "2024-Q4",
  computed_at: "2026-07-10T00:00:00Z",
} as NeighborhoodReport;

describe("Report Back to dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiFetch).mockResolvedValue(mockReport);
  });

  it("shows Back to dashboard when signed in", async () => {
    authMock.mockResolvedValue({ user: { email: "a@example.com" } });

    const ui = await ReportPage({
      params: Promise.resolve({ addressId: "demo-address-001" }),
    });
    render(ui);

    expect(screen.getByRole("link", { name: /back to dashboard/i })).toHaveAttribute(
      "href",
      "/dashboard",
    );
  });

  it("hides Back to dashboard when guest", async () => {
    authMock.mockResolvedValue(null);

    const ui = await ReportPage({
      params: Promise.resolve({ addressId: "demo-address-001" }),
    });
    render(ui);

    expect(screen.queryByRole("link", { name: /back to dashboard/i })).not.toBeInTheDocument();
  });
});
