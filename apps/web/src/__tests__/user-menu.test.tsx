import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UserMenu from "@/components/layout/UserMenu";

vi.mock("next-auth/react", () => ({
  signOut: vi.fn(),
  useSession: vi.fn(),
}));

import { useSession } from "next-auth/react";

const mockUseSession = vi.mocked(useSession);

describe("UserMenu", () => {
  it("renders user name and menu items when signed in", async () => {
    const user = userEvent.setup();
    mockUseSession.mockReturnValue({
      data: {
        user: { name: "Alice Smith", email: "alice@example.com" },
        expires: "2099-01-01T00:00:00.000Z",
      },
      status: "authenticated",
      update: vi.fn(),
    });

    render(<UserMenu />);
    expect(screen.getByText("Alice Smith")).toBeInTheDocument();

    await user.click(screen.getByRole("button"));

    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /plans & upgrade/i })).toHaveAttribute(
      "href",
      "/pricing",
    );
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });

  it("renders nothing when signed out", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
      update: vi.fn(),
    });
    const { container } = render(<UserMenu />);
    expect(container.firstChild).toBeNull();
  });
});
