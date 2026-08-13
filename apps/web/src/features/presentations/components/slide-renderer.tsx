import type { Slide } from "@gapo-slidegen/contracts";

import { cn } from "@/lib/cn";

interface SlideRendererProps {
  slide: Slide;
  className?: string;
}

export function SlideRenderer({ slide, className }: SlideRendererProps) {
  return (
    <article
      className={cn(
        "aspect-video w-full overflow-hidden rounded-xl bg-[#edf5f1] text-[#17342b] shadow-[0_24px_70px_rgba(28,61,51,0.16)]",
        className,
      )}
    >
      {renderSlide(slide)}
    </article>
  );
}

function renderSlide(slide: Slide) {
  switch (slide.layout) {
    case "title":
      return (
        <div className="flex h-full flex-col justify-between p-[7%]">
          <p className="text-[clamp(0.55rem,1.2vw,0.95rem)] font-semibold text-[#176b55]">
            Gapo SlideGen
          </p>
          <div>
            <h2 className="max-w-[80%] text-[clamp(1.5rem,5vw,4.75rem)] font-semibold leading-[1.03] tracking-[-0.045em]">
              {slide.title}
            </h2>
            {slide.body.subtitle ? (
              <p className="mt-[3%] max-w-[65%] text-[clamp(0.65rem,1.6vw,1.35rem)] leading-relaxed text-[#4f675e]">
                {slide.body.subtitle}
              </p>
            ) : null}
          </div>
          <p className="text-[clamp(0.45rem,0.9vw,0.75rem)] text-[#6b7d76]">
            Demo data
          </p>
        </div>
      );
    case "title_bullets":
      return (
        <div className="grid h-full grid-cols-[0.8fr_1.2fr] gap-[6%] p-[7%]">
          <h2 className="text-[clamp(1.2rem,3.6vw,3.5rem)] font-semibold leading-[1.05] tracking-[-0.04em]">
            {slide.title}
          </h2>
          <ul className="grid content-center gap-[6%]">
            {slide.body.bullets.map((bullet) => (
              <li key={bullet} className="border-l-2 border-[#278f72] pl-[5%] text-[clamp(0.65rem,1.55vw,1.25rem)] leading-relaxed">
                {bullet}
              </li>
            ))}
          </ul>
        </div>
      );
    case "two_column":
      return (
        <div className="flex h-full flex-col p-[6%]">
          <h2 className="text-[clamp(1.2rem,3vw,3rem)] font-semibold tracking-[-0.04em]">
            {slide.title}
          </h2>
          <div className="mt-[5%] grid flex-1 grid-cols-2 gap-[4%]">
            <SlideColumn title={slide.body.left_title} points={slide.body.left_points} />
            <SlideColumn title={slide.body.right_title} points={slide.body.right_points} />
          </div>
        </div>
      );
    case "statistic":
      return (
        <div className="grid h-full grid-cols-[1.15fr_0.85fr]">
          <div className="flex flex-col justify-between p-[7%]">
            <h2 className="text-[clamp(1rem,2.5vw,2.5rem)] font-semibold tracking-tight">
              {slide.title}
            </h2>
            <div>
              <p className="text-[clamp(2.5rem,9vw,8.5rem)] font-semibold leading-none tracking-[-0.06em] text-[#176b55]">
                {slide.body.value}
              </p>
              <p className="mt-[3%] text-[clamp(0.7rem,1.8vw,1.4rem)] font-medium">
                {slide.body.label}
              </p>
            </div>
          </div>
          <div className="flex items-end bg-[#176b55] p-[10%] text-[clamp(0.65rem,1.4vw,1.1rem)] leading-relaxed text-white">
            {slide.body.context}
          </div>
        </div>
      );
    case "quote":
      return (
        <div className="flex h-full flex-col justify-center p-[10%]">
          <p className="max-w-[90%] text-[clamp(1.2rem,4vw,4rem)] font-semibold leading-[1.12] tracking-[-0.035em]">
            “{slide.body.quote}”
          </p>
          {slide.body.attribution ? (
            <p className="mt-[5%] text-[clamp(0.55rem,1.2vw,0.95rem)] font-medium text-[#4f675e]">
              {slide.body.attribution}
            </p>
          ) : null}
        </div>
      );
  }
}

function SlideColumn({ title, points }: { title: string; points: string[] }) {
  return (
    <section className="rounded-lg bg-white/55 p-[8%]">
      <h3 className="text-[clamp(0.75rem,1.7vw,1.4rem)] font-semibold text-[#176b55]">
        {title}
      </h3>
      <ul className="mt-[8%] grid gap-[8%] text-[clamp(0.55rem,1.25vw,1rem)] leading-relaxed text-[#395047]">
        {points.map((point) => <li key={point}>{point}</li>)}
      </ul>
    </section>
  );
}
