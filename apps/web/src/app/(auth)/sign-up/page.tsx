import Link from "next/link";

import { AuthForm } from "@/features/auth/components/auth-form";

export const metadata = { title: "Create account" };

export default function SignUpPage() {
  return (
    <div className="w-full max-w-sm">
      <Link href="/" className="mb-10 block text-lg font-semibold lg:hidden">
        Gapo SlideGen
      </Link>
      <h1 className="text-3xl font-semibold tracking-tight">Create an account</h1>
      <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
        Start with a private workspace for your presentations.
      </p>
      <AuthForm mode="sign-up" />
      <p className="mt-6 text-sm text-[var(--text-muted)]">
        Already have an account?{" "}
        <Link className="font-semibold text-[var(--accent)]" href="/sign-in">
          Sign in
        </Link>
      </p>
    </div>
  );
}
