import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import DiscoverCoverageBanner from "@/components/discover/DiscoverCoverageBanner";

describe("DiscoverCoverageBanner", () => {
  it("shows empty message when scored_count is 0", () => {
    render(<DiscoverCoverageBanner scoredCount={0} unscoredCount={0} />);
    expect(screen.getByText(/no scored neighborhoods here yet/i)).toBeInTheDocument();
  });

  it("shows partial coverage when mixed", () => {
    render(<DiscoverCoverageBanner scoredCount={10} unscoredCount={3} />);
    expect(screen.getByText(/partial coverage/i)).toBeInTheDocument();
    expect(screen.getByText(/3 unscored/i)).toBeInTheDocument();
  });

  it("renders nothing when fully scored and not truncated", () => {
    const { container } = render(
      <DiscoverCoverageBanner scoredCount={5} unscoredCount={0} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
