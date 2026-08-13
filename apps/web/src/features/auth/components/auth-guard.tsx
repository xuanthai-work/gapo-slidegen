"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

import { getCurrentUser } from "../api";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const query = useQuery({
    queryKey: ["auth", "me"],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 60_000,
  });

  const isUnauthorized = query.error instanceof ApiError && query.error.status === 401;

  useEffect(() => {
    if (isUnauthorized) {
      router.replace("/sign-in");
    }
  }, [isUnauthorized, router]);

  if (query.isPending || isUnauthorized) {
    return <AuthLoading />;
  }

  if (query.isError) {
    return (
      <main className="grid min-h-[100dvh] place-items-center px-4">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-semibold">Could not connect to the backend</h1>
          <p className="mt-3 text-sm leading-relaxed text-[var(--text-muted)]">
            Check that FastAPI is running at the configured address, then try again.
          </p>
          <Button className="mt-6" onClick={() => query.refetch()}>
            Try again
          </Button>
        </div>
      </main>
    );
  }

  return children;
}

function AuthLoading() {
  return (
    <main className="grid min-h-[100dvh] place-items-center px-4" aria-label="Checking your session">
      <div className="w-full max-w-xs animate-pulse">
        <div className="mx-auto size-10 rounded-lg bg-[var(--surface-muted)]" />
        <div className="mx-auto mt-5 h-4 w-40 rounded bg-[var(--surface-muted)]" />
      </div>
    </main>
  );
}
