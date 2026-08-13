import type { ReactNode } from "react";

import { AuthGuard } from "@/features/auth/components/auth-guard";

import { AppShell } from "./_components/app-shell";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
