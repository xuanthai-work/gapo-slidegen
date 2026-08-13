"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getCurrentUser, signIn, signUp } from "../api";

function authErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }
  return "Could not authenticate with Neon Auth. Please try again.";
}

export function AuthForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    try {
      const result =
        mode === "sign-up"
          ? await signUp({
              email,
              password,
              display_name: String(formData.get("display_name") ?? "") || undefined,
            })
          : await signIn({ email, password });

      if (result.error) {
        throw new Error(result.error.message || "Authentication failed");
      }

      const user = await getCurrentUser();
      queryClient.setQueryData(["auth", "me"], user);
      router.replace("/dashboard");
      router.refresh();
    } catch (caughtError) {
      setError(authErrorMessage(caughtError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="mt-8 grid gap-5" onSubmit={handleSubmit}>
      {mode === "sign-up" ? (
        <label className="grid gap-2 text-sm font-medium">
          Display name
          <Input name="display_name" autoComplete="name" maxLength={120} />
        </label>
      ) : null}
      <label className="grid gap-2 text-sm font-medium">
        Email
        <Input name="email" type="email" autoComplete="email" maxLength={320} required />
      </label>
      <label className="grid gap-2 text-sm font-medium">
        Password
        <Input
          name="password"
          type="password"
          autoComplete={mode === "sign-up" ? "new-password" : "current-password"}
          minLength={8}
          maxLength={128}
          aria-describedby={mode === "sign-up" ? "password-hint" : undefined}
          required
        />
        {mode === "sign-up" ? (
          <span id="password-hint" className="text-xs font-normal text-[var(--text-subtle)]">
            At least 8 characters.
          </span>
        ) : null}
      </label>
      {error ? (
        <p role="alert" className="rounded-lg bg-[color-mix(in_srgb,var(--danger)_12%,transparent)] px-3 py-2.5 text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
      <Button type="submit" className="mt-1 w-full" disabled={isSubmitting}>
        {isSubmitting
          ? "Working…"
          : mode === "sign-up"
            ? "Create account"
            : "Sign in"}
      </Button>
    </form>
  );
}
