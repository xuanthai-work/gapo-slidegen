"use client";

import { ArrowRight, Clock, FileText, Plus } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { listPresentations } from "@/features/presentations/api";

const statusLabels = {
  draft: "Draft",
  outlining: "Generating outline",
  generating: "Generating slides",
  ready: "Ready",
  failed: "Needs attention",
} as const;

function relativeDate(value: string): string {
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

export function DashboardContent() {
  const query = useQuery({
    queryKey: ["presentations"],
    queryFn: listPresentations,
  });

  return (
    <section
      id="presentations"
      className="mt-10 grid gap-8 xl:grid-cols-[minmax(0,1.7fr)_minmax(18rem,0.7fr)]"
    >
      <div>
        <div className="flex items-center justify-between gap-4 border-b border-[var(--line)] pb-4">
          <h2 className="text-lg font-semibold">Recent</h2>
          <span className="text-sm text-[var(--text-subtle)]">
            {query.data ? `${query.data.length} presentations` : "Loading…"}
          </span>
        </div>

        {query.isError ? (
          <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
            <p className="font-medium">Could not load your presentations.</p>
            <Button className="mt-4" variant="secondary" onClick={() => query.refetch()}>
              Try again
            </Button>
          </div>
        ) : null}

        {query.isPending ? (
          <div className="grid gap-3 pt-4 sm:grid-cols-2" aria-label="Loading presentations">
            {[0, 1].map((item) => (
              <div key={item} className="h-48 animate-pulse rounded-xl bg-[var(--surface-muted)]" />
            ))}
          </div>
        ) : null}

        {query.data?.length === 0 ? (
          <div className="mt-4 rounded-xl border border-dashed border-[var(--line)] p-8 text-center">
            <p className="font-medium">No presentations yet</p>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Create one from a prompt and review the AI-generated outline.
            </p>
          </div>
        ) : null}

        {query.data?.length ? (
          <div className="grid gap-3 pt-4 sm:grid-cols-2">
            {query.data.map((presentation) => (
              <Link
                key={presentation.id}
                href={`/presentations/${presentation.id}/outline`}
                className="group rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 transition-[border-color,transform] hover:border-[var(--accent)] active:translate-y-px"
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="grid size-10 place-items-center rounded-lg bg-[var(--surface-muted)] text-[var(--accent)]">
                    <FileText size={21} aria-hidden="true" />
                  </span>
                  <ArrowRight size={18} className="text-[var(--text-subtle)] transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </div>
                <h3 className="mt-8 text-lg font-semibold leading-snug">{presentation.title}</h3>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--text-subtle)]">
                  <span>{statusLabels[presentation.status]}</span>
                  <span>{presentation.slide_count} slides</span>
                </div>
                <p className="mt-5 flex items-center gap-1.5 text-xs text-[var(--text-subtle)]">
                  <Clock size={14} aria-hidden="true" />
                  Updated {relativeDate(presentation.updated_at)}
                </p>
              </Link>
            ))}
          </div>
        ) : null}
      </div>

      <aside className="rounded-xl bg-[var(--accent)] p-6 text-white xl:self-start">
        <Plus size={24} weight="bold" aria-hidden="true" />
        <h2 className="mt-8 text-2xl font-semibold tracking-tight">Start with a topic</h2>
        <p className="mt-3 text-sm leading-relaxed text-white/80">
          AI drafts the outline first, so you can shape the story before slides are generated.
        </p>
        <Button asChild variant="secondary" className="mt-6 border-white/30 bg-white text-[#105743] hover:bg-white/90">
          <Link href="/presentations/new">Create presentation</Link>
        </Button>
      </aside>
    </section>
  );
}
