"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import AuthFormFields from "@/components/auth/AuthFormFields";
import { ButtonWithArrow } from "@/components/ui/Button";
import { isValidEmailShape } from "@/lib/api";

function safeCallbackUrl(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) {
    return "/dashboard";
  }
  return raw;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = safeCallbackUrl(searchParams.get("callbackUrl"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!isValidEmailShape(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (!password) {
      setError("Enter your password.");
      return;
    }

    setLoading(true);

    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        // Auth.js Credentials returns CredentialsSignin for bad auth —
        // never enumerate email vs password; never call this "something went wrong".
        setError("Invalid email or password.");
      } else if (result?.ok === false) {
        setError("Something went wrong. Please try again.");
      } else {
        router.push(callbackUrl);
        router.refresh();
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-display text-3xl font-bold tracking-tight text-foreground">
          Welcome back
        </h1>
        <p className="text-muted-foreground text-sm">
          Sign in to your NeighborhoodInsight account.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <AuthFormFields
          email={email}
          password={password}
          onEmailChange={setEmail}
          onPasswordChange={setPassword}
          error={error}
          disabled={loading}
        />

        <ButtonWithArrow type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </ButtonWithArrow>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        No account?{" "}
        <Link
          href="/register"
          className="font-semibold text-primary hover:opacity-80 transition-opacity"
        >
          Create one free
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4 animate-pulse" aria-busy="true" aria-label="Loading sign in">
          <div className="h-9 w-48 rounded-lg bg-muted" />
          <div className="h-4 w-64 rounded bg-muted" />
          <div className="h-40 rounded-xl bg-muted" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
