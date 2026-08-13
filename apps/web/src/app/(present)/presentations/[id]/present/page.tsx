import { ArrowLeft, CornersOut } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SlideRenderer } from "@/features/presentations/components/slide-renderer";
import { sampleTitleSlide } from "@/features/presentations/sample-data";

export const metadata = { title: "Present" };

export default async function PresentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <main className="flex min-h-[100dvh] flex-col bg-[#101815] p-3 text-[#edf5f1] sm:p-5">
      <header className="flex min-h-12 items-center justify-between gap-4">
        <Button asChild variant="ghost" className="text-[#c5d3ce] hover:bg-white/10 hover:text-white">
          <Link href={`/presentations/${id}/edit`}>
            <ArrowLeft size={18} aria-hidden="true" />
            Exit
          </Link>
        </Button>
        <p className="font-mono text-xs text-[#91a59d]">1 / 4</p>
        <Button variant="ghost" className="text-[#c5d3ce] hover:bg-white/10 hover:text-white" aria-label="Enter full screen">
          <CornersOut size={19} aria-hidden="true" />
        </Button>
      </header>
      <section className="grid flex-1 place-items-center py-4">
        <SlideRenderer
          slide={sampleTitleSlide}
          className="max-w-6xl shadow-[0_32px_90px_rgba(0,0,0,0.35)]"
        />
      </section>
    </main>
  );
}
