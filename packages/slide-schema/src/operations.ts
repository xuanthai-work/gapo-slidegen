import { z } from "zod";
import {
  parsePresentation,
  presentationSchema,
  slideElementSchema,
  slideSchema,
  type Presentation,
  type SlideElement,
} from "./schema";

const operationBaseSchema = z.object({
  operationId: z.string().trim().min(1),
});

export const editOperationSchema = z.discriminatedUnion("type", [
  operationBaseSchema.extend({
    type: z.literal("replace-presentation"),
    presentation: presentationSchema,
  }),
  operationBaseSchema.extend({
    type: z.literal("add-slide"),
    index: z.number().int().nonnegative(),
    slide: slideSchema,
  }),
  operationBaseSchema.extend({
    type: z.literal("remove-slide"),
    slideId: z.string().trim().min(1),
  }),
  operationBaseSchema.extend({
    type: z.literal("move-slide"),
    slideId: z.string().trim().min(1),
    index: z.number().int().nonnegative(),
  }),
  operationBaseSchema.extend({
    type: z.literal("replace-slide"),
    slideId: z.string().trim().min(1),
    slide: slideSchema,
  }),
  operationBaseSchema.extend({
    type: z.literal("upsert-element"),
    slideId: z.string().trim().min(1),
    element: slideElementSchema,
  }),
  operationBaseSchema.extend({
    type: z.literal("remove-element"),
    slideId: z.string().trim().min(1),
    elementId: z.string().trim().min(1),
  }),
]);

export type EditOperation = z.infer<typeof editOperationSchema>;

export class EditOperationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EditOperationError";
  }
}

function replaceElement(
  elements: SlideElement[],
  nextElement: SlideElement,
): { elements: SlideElement[]; replaced: boolean } {
  let replaced = false;
  const next = elements.map((element) => {
    if (element.id === nextElement.id) {
      replaced = true;
      return nextElement;
    }

    if ("children" in element && Array.isArray(element.children)) {
      const nested = replaceElement(element.children, nextElement);
      if (nested.replaced) {
        replaced = true;
        return { ...element, children: nested.elements } as SlideElement;
      }
    }

    if ("child" in element && element.child) {
      const nested = replaceElement([element.child], nextElement);
      if (nested.replaced) {
        replaced = true;
        return { ...element, child: nested.elements[0] } as SlideElement;
      }
    }

    return element;
  });

  return { elements: next, replaced };
}

function removeElement(
  elements: SlideElement[],
  elementId: string,
): { elements: SlideElement[]; removed: boolean } {
  let removed = false;
  const next: SlideElement[] = [];

  for (const element of elements) {
    if (element.id === elementId) {
      removed = true;
      continue;
    }

    if ("children" in element && Array.isArray(element.children)) {
      const nested = removeElement(element.children, elementId);
      removed ||= nested.removed;
      next.push({ ...element, children: nested.elements } as SlideElement);
      continue;
    }

    if ("child" in element && element.child) {
      if (element.child.id === elementId) {
        removed = true;
        next.push({ ...element, child: null } as SlideElement);
      } else {
        const nested = removeElement([element.child], elementId);
        removed ||= nested.removed;
        next.push({ ...element, child: nested.elements[0] ?? null } as SlideElement);
      }
      continue;
    }

    next.push(element);
  }

  return { elements: next, removed };
}

export function applyEditOperation(
  current: Presentation,
  unsafeOperation: EditOperation,
): Presentation {
  const operation = editOperationSchema.parse(unsafeOperation);

  if (operation.type === "replace-presentation") {
    return parsePresentation(operation.presentation);
  }

  let next: Presentation = structuredClone(current);

  if (operation.type === "add-slide") {
    if (next.slides.some((slide) => slide.id === operation.slide.id)) {
      throw new EditOperationError(`Slide ${operation.slide.id} already exists`);
    }
    next.slides.splice(Math.min(operation.index, next.slides.length), 0, operation.slide);
  } else if (operation.type === "remove-slide") {
    const length = next.slides.length;
    next.slides = next.slides.filter((slide) => slide.id !== operation.slideId);
    if (next.slides.length === length) {
      throw new EditOperationError(`Slide ${operation.slideId} was not found`);
    }
  } else if (operation.type === "move-slide") {
    const from = next.slides.findIndex((slide) => slide.id === operation.slideId);
    if (from < 0) throw new EditOperationError(`Slide ${operation.slideId} was not found`);
    const [slide] = next.slides.splice(from, 1);
    if (!slide) throw new EditOperationError(`Slide ${operation.slideId} was not found`);
    next.slides.splice(Math.min(operation.index, next.slides.length), 0, slide);
  } else if (operation.type === "replace-slide") {
    const index = next.slides.findIndex((slide) => slide.id === operation.slideId);
    if (index < 0) throw new EditOperationError(`Slide ${operation.slideId} was not found`);
    next.slides[index] = operation.slide;
  } else {
    const slide = next.slides.find((candidate) => candidate.id === operation.slideId);
    if (!slide) throw new EditOperationError(`Slide ${operation.slideId} was not found`);

    if (operation.type === "upsert-element") {
      const result = replaceElement(slide.elements, operation.element);
      slide.elements = result.replaced
        ? result.elements
        : [...slide.elements, operation.element];
    } else {
      const result = removeElement(slide.elements, operation.elementId);
      if (!result.removed) {
        throw new EditOperationError(`Element ${operation.elementId} was not found`);
      }
      slide.elements = result.elements;
    }

    slide.revision += 1;
  }

  next.revision += 1;
  return parsePresentation(next);
}
