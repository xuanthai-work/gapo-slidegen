export type PresentationStatus =
  | "draft"
  | "outlining"
  | "generating"
  | "ready"
  | "failed";

export type SlideLayout =
  | "title"
  | "title_bullets"
  | "two_column"
  | "statistic"
  | "quote"
;

interface SlideBase {
  id: string;
  title: string;
  speaker_notes?: string | null;
  image_prompt?: string | null;
}

export interface TitleSlide extends SlideBase {
  layout: "title";
  body: { subtitle?: string | null };
}

export interface TitleBulletsSlide extends SlideBase {
  layout: "title_bullets";
  body: { bullets: string[] };
}

export interface TwoColumnSlide extends SlideBase {
  layout: "two_column";
  body: {
    left_title: string;
    left_points: string[];
    right_title: string;
    right_points: string[];
  };
}

export interface StatisticSlide extends SlideBase {
  layout: "statistic";
  body: { value: string; label: string; context?: string | null };
}

export interface QuoteSlide extends SlideBase {
  layout: "quote";
  body: { quote: string; attribution?: string | null };
}

export type Slide =
  | TitleSlide
  | TitleBulletsSlide
  | TwoColumnSlide
  | StatisticSlide
  | QuoteSlide;

export interface OutlineItem {
  id: string;
  title: string;
  objective: string;
  key_points: string[];
}

export interface PresentationSummary {
  id: string;
  title: string;
  status: PresentationStatus;
  slide_count: number;
  updated_at: string;
}
