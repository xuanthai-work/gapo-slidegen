import {
  applyEditOperation,
  parsePresentation,
  type EditOperation,
  type Presentation,
} from "@gapo-slidegen/slide-schema";

export type EditorChange = {
  document: Presentation;
  operation: EditOperation;
};

export type EditorBoundaryOptions = {
  initialDocument: unknown;
  onChange: (change: EditorChange) => void;
};

export class EditorBoundary {
  readonly #onChange: (change: EditorChange) => void;
  #document: Presentation;

  constructor(options: EditorBoundaryOptions) {
    this.#document = parsePresentation(options.initialDocument);
    this.#onChange = options.onChange;
  }

  get document(): Presentation {
    return structuredClone(this.#document);
  }

  apply(operation: EditOperation): Presentation {
    this.#document = applyEditOperation(this.#document, operation);
    const document = this.document;
    this.#onChange({ document, operation });
    return document;
  }

  replaceFromPersistence(input: unknown): Presentation {
    this.#document = parsePresentation(input);
    return this.document;
  }
}
