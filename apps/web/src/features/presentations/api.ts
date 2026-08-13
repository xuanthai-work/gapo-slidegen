import type { components } from "@gapo-slidegen/contracts";

import { apiFetch } from "@/lib/api/client";

export type Outline = components["schemas"]["Outline"];
export type OutlineSlide = components["schemas"]["OutlineSlide"];
export type PresentationCreate = components["schemas"]["PresentationCreate"];
export type PresentationDetail = components["schemas"]["PresentationDetail"];
export type PresentationSummary = components["schemas"]["PresentationSummary"];

export function listPresentations(): Promise<PresentationSummary[]> {
  return apiFetch("/api/v1/presentations");
}

export function createPresentation(payload: PresentationCreate): Promise<PresentationDetail> {
  return apiFetch("/api/v1/presentations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPresentation(id: string): Promise<PresentationDetail> {
  return apiFetch(`/api/v1/presentations/${id}`);
}

export function generateOutline(id: string): Promise<Outline> {
  return apiFetch(`/api/v1/presentations/${id}/outline/generate`, { method: "POST" });
}

export function saveOutline(id: string, outline: Outline): Promise<Outline> {
  return apiFetch(`/api/v1/presentations/${id}/outline`, {
    method: "PUT",
    body: JSON.stringify(outline),
  });
}
