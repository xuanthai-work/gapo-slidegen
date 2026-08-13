"use client";

import { SignOut } from "@phosphor-icons/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

import { getCurrentUser, signOut } from "../api";

export function UserMenu() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const userQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: getCurrentUser,
    staleTime: 60_000,
  });
  const logoutMutation = useMutation({
    mutationFn: async () => {
      const result = await signOut();
      if (result.error) throw new Error(result.error.message);
    },
    onSettled: async () => {
      queryClient.removeQueries({ queryKey: ["auth"] });
      router.replace("/sign-in");
      router.refresh();
    },
  });

  const user = userQuery.data;

  return (
    <div>
      <div className="px-3 text-sm">
        <p className="truncate font-medium">{user?.display_name || "Your account"}</p>
        <p className="mt-0.5 truncate text-xs text-[var(--text-subtle)]">
          {user?.email || "Loading…"}
        </p>
      </div>
      <Button
        type="button"
        variant="ghost"
        className="mt-3 w-full justify-start"
        disabled={logoutMutation.isPending}
        onClick={() => logoutMutation.mutate()}
      >
        <SignOut size={18} aria-hidden="true" />
        {logoutMutation.isPending ? "Signing out…" : "Sign out"}
      </Button>
    </div>
  );
}
