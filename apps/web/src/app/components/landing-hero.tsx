export interface LandingHeroProps {
  eyebrow?: string;
  heading: string;
  body?: string;
  align?: "left" | "center";
}

export function LandingHero({ eyebrow, heading, body, align = "left" }: LandingHeroProps) {
  return (
    <section className={`landing-hero landing-hero--${align}`}>
      {eyebrow ? <p className="landing-hero__eyebrow eyebrow">{eyebrow}</p> : null}
      <h1 className="landing-hero__heading">{heading}</h1>
      {body ? <p className="landing-hero__body">{body}</p> : null}
    </section>
  );
}
