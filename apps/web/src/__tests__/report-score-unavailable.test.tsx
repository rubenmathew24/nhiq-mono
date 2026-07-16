import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

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

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number;
    code?: string;
    constructor(message: string, status: number, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  }
  return {
    ApiError,
    apiFetch: vi.fn(),
  };
});

import { ApiError, apiFetch } from "@/lib/api";
import ReportPage from "@/app/report/[addressId]/page";

describe("Report SCORE_UNAVAILABLE", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.mockResolvedValue(null);
  });

  it("shows specific unavailable copy instead of fake scores", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError(
        "Neighborhood score is not available for this address yet.",
        404,
        "SCORE_UNAVAILABLE",
      ),
    );

    const ui = await ReportPage({
      params: Promise.resolve({ addressId: "some-address-id" }),
    });
    render(ui);

    expect(
      screen.getByRole("heading", { name: /score not available yet/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/not available for this address yet/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/82/)).not.toBeInTheDocument();
  });
});
