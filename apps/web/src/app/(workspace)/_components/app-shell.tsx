import {
  Files,
  House,
  Plus,
  Sparkle,
} from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { UserMenu } from "@/features/auth/components/user-menu";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: House },
  { href: "/dashboard#presentations", label: "Presentations", icon: Files },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-[100dvh] lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="hidden border-r border-[var(--line)] bg-[var(--surface)] lg:flex lg:flex-col lg:p-4">
        <Link href="/dashboard" className="flex h-12 items-center gap-3 px-2 font-semibold tracking-tight">
          <span className="grid size-8 place-items-center rounded-lg bg-[var(--accent)] text-white">
            <Sparkle size={17} weight="fill" aria-hidden="true" />
          </span>
          Gapo SlideGen
        </Link>
        <nav className="mt-7 grid gap-1" aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex min-h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]"
            >
              <Icon size={18} aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-[var(--line)] pt-4">
          <UserMenu />
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--background)_92%,transparent)] px-4 backdrop-blur-lg sm:px-6 lg:px-8">
          <Link href="/dashboard" className="font-semibold lg:hidden">
            Gapo SlideGen
          </Link>
          <p className="hidden text-sm text-[var(--text-muted)] lg:block">
            Personal workspace
          </p>
          <Button asChild>
            <Link href="/presentations/new">
              <Plus size={17} weight="bold" aria-hidden="true" />
              Create presentation
            </Link>
          </Button>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
