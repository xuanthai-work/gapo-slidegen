import Link from "next/link";

import { AuthForm } from "@/features/auth/components/auth-form";

export const metadata = { title: "Sign in" };

export default function SignInPage() {
  return (
    <div className="w-full max-w-sm">
      <Link href="/" className="mb-10 block text-lg font-semibold lg:hidden">
        Gapo SlideGen
      </Link>
      <h1 className="text-3xl font-semibold tracking-tight">Sign in</h1>
      <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
        Reopen your presentations and continue where you left off.
      </p>
      <AuthForm mode="sign-in" />
      <p className="mt-6 text-sm text-[var(--text-muted)]">
        New to SlideGen?{" "}
        <Link className="font-semibold text-[var(--accent)]" href="/sign-up">
          Create an account
        </Link>
      </p>
    </div>
  );
}
