import { ArrowsClockwise, DotsSixVertical, Play } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SlideRenderer } from "@/features/presentations/components/slide-renderer";
import { sampleTitleSlide } from "@/features/presentations/sample-data";

const slides = [
  "AI in business operations",
  "Context and opportunity",
  "Three priority use cases",
  "The 90-day roadmap",
];

export const metadata = { title: "Edit presentation" };

export default async function EditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="min-h-[calc(100dvh-4rem)] lg:grid lg:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="border-b border-[var(--line)] bg-[var(--surface)] p-4 lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Slides</p>
            <p className="mt-0.5 text-xs text-[var(--text-subtle)]">Sample data</p>
          </div>
          <Button variant="ghost" aria-label="Regenerate slide">
            <ArrowsClockwise size={18} aria-hidden="true" />
          </Button>
        </div>
        <ol className="mt-4 flex gap-3 overflow-x-auto pb-2 lg:grid lg:overflow-visible">
          {slides.map((slide, index) => (
            <li key={slide} className="min-w-48 lg:min-w-0">
              <button
                type="button"
                className="grid w-full grid-cols-[auto_minmax(0,1fr)] gap-2 rounded-lg border border-[var(--line)] bg-[var(--background)] p-2 text-left hover:border-[var(--accent)]"
              >
                <DotsSixVertical size={17} className="mt-1 text-[var(--text-subtle)]" aria-hidden="true" />
                <span>
                  <span className="block font-mono text-[10px] text-[var(--text-subtle)]">{index + 1}</span>
                  <span className="mt-1 line-clamp-2 block text-xs font-medium leading-relaxed">{slide}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      </aside>

      <section className="min-w-0 p-4 sm:p-6 lg:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">AI in business operations</h1>
            <p className="mt-1 text-xs text-[var(--text-subtle)]">Autosaved</p>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="secondary">
              <Link href={`/presentations/${id}/outline`}>Outline</Link>
            </Button>
            <Button asChild>
              <Link href={`/presentations/${id}/present`}>
                <Play size={17} weight="fill" aria-hidden="true" />
                Present
              </Link>
            </Button>
          </div>
        </div>

        <div className="mt-6 grid min-h-[34rem] place-items-center rounded-xl bg-[var(--surface-muted)] p-4 sm:p-8">
          <SlideRenderer slide={sampleTitleSlide} className="max-w-4xl" />
        </div>
      </section>
    </div>
  );
}
