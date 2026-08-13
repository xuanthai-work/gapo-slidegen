import type { ReactNode } from "react";

import { AuthGuard } from "@/features/auth/components/auth-guard";

export default function PresentLayout({ children }: { children: ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
