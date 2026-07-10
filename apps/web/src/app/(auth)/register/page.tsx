"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import AuthFormFields from "@/components/auth/AuthFormFields";
import { ButtonWithArrow } from "@/components/ui/Button";
import { apiFetch, ApiError, isValidEmailShape } from "@/lib/api";
import type { User } from "@/types/api";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!fullName.trim()) {
      setError("Enter your full name.");
      return;
    }
    if (!isValidEmailShape(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      await apiFetch<User>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName }),
      });

      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Account created but sign-in failed. Please sign in manually.");
        router.push("/login");
      } else {
        router.push("/dashboard");
        router.refresh();
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError(
            "An account with this email already exists. Sign in instead?",
          );
        } else if (err.status === 422 || err.status === 400) {
          setError(err.message || "Enter a valid email address.");
        } else if (err.status === 0 || err.status >= 500) {
          setError("Something went wrong. Please try again.");
        } else {
          setError(err.message || "Something went wrong. Please try again.");
        }
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
          Create your account
        </h1>
        <p className="text-muted-foreground text-sm">
          Free — 3 address lookups per month. No credit card required.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <AuthFormFields
          showFullName
          fullName={fullName}
          email={email}
          password={password}
          onFullNameChange={setFullName}
          onEmailChange={setEmail}
          onPasswordChange={setPassword}
          error={error}
          disabled={loading}
        />

        <ButtonWithArrow type="submit" className="w-full" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </ButtonWithArrow>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-semibold text-primary hover:opacity-80 transition-opacity"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
