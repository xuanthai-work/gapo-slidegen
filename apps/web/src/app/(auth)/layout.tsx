import Link from "next/link";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="grid min-h-[100dvh] lg:grid-cols-[minmax(0,0.85fr)_minmax(34rem,1.15fr)]">
      <section className="hidden bg-[var(--accent)] p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Gapo SlideGen
        </Link>
        <div className="max-w-xl">
          <p className="text-4xl font-semibold leading-tight tracking-[-0.035em]">
            From an idea to a structured slide deck.
          </p>
          <p className="mt-5 max-w-md text-base leading-relaxed text-white/80">
            Shape the outline, follow generation progress, and refine every slide
            before you present.
          </p>
        </div>
        <p className="text-sm text-white/70">AI assists. You stay in control.</p>
      </section>
      <section className="grid place-items-center px-4 py-12 sm:px-8">
        {children}
      </section>
    </main>
  );
}
