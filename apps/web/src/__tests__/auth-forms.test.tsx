import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthFormFields from "@/components/auth/AuthFormFields";
import { formatApiDetail, isValidEmailShape } from "@/lib/api";

describe("AuthFormFields", () => {
  it("renders email and password inputs", () => {
    render(
      <AuthFormFields
        email=""
        password=""
        onEmailChange={() => {}}
        onPasswordChange={() => {}}
      />,
    );
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("displays an error message when error prop is provided", () => {
    render(
      <AuthFormFields
        email=""
        password=""
        onEmailChange={() => {}}
        onPasswordChange={() => {}}
        error="Invalid credentials"
      />,
    );
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
  });

  it("calls onChange handlers on input", async () => {
    const user = userEvent.setup();
    const onEmail = vi.fn();
    const onPassword = vi.fn();
    render(
      <AuthFormFields
        email=""
        password=""
        onEmailChange={onEmail}
        onPasswordChange={onPassword}
      />,
    );
    await user.type(screen.getByLabelText(/email/i), "a");
    expect(onEmail).toHaveBeenCalled();
  });
});

describe("isValidEmailShape", () => {
  it("rejects incomplete emails like testing@t", () => {
    expect(isValidEmailShape("testing@t")).toBe(false);
  });

  it("accepts a normal email", () => {
    expect(isValidEmailShape("user@example.com")).toBe(true);
  });
});

describe("formatApiDetail", () => {
  it("returns string detail as-is", () => {
    expect(formatApiDetail("Duplicate email", "fallback")).toBe("Duplicate email");
  });

  it("turns FastAPI validation array into a readable email message", () => {
    const detail = [
      {
        type: "value_error",
        loc: ["body", "email"],
        msg: "value is not a valid email address",
      },
    ];
    expect(formatApiDetail(detail, "fallback")).toBe("Enter a valid email address.");
  });

  it("uses fallback when detail is empty", () => {
    expect(formatApiDetail(undefined, "Something went wrong")).toBe(
      "Something went wrong",
    );
  });
});
