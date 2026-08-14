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
  #past: Presentation[] = [];
  #future: Presentation[] = [];

  constructor(options: EditorBoundaryOptions) {
    this.#document = parsePresentation(options.initialDocument);
    this.#onChange = options.onChange;
  }

  get document(): Presentation {
    return structuredClone(this.#document);
  }

  get canUndo(): boolean {
    return this.#past.length > 0;
  }

  get canRedo(): boolean {
    return this.#future.length > 0;
  }

  #emitReplacement(document: Presentation, operationId: string): Presentation {
    this.#document = {
      ...structuredClone(document),
      revision: this.#document.revision + 1,
    };
    const next = this.document;
    this.#onChange({
      document: next,
      operation: {
        operationId,
        type: "replace-presentation",
        presentation: next,
      },
    });
    return next;
  }

  apply(operation: EditOperation): Presentation {
    const previous = this.document;
    const next = applyEditOperation(this.#document, operation);
    this.#past.push(previous);
    if (this.#past.length > 100) this.#past.shift();
    this.#future = [];
    this.#document = next;
    const document = this.document;
    this.#onChange({ document, operation });
    return document;
  }

  undo(): Presentation | null {
    const previous = this.#past.pop();
    if (!previous) return null;
    this.#future.push(this.document);
    return this.#emitReplacement(previous, "history-undo");
  }

  redo(): Presentation | null {
    const next = this.#future.pop();
    if (!next) return null;
    this.#past.push(this.document);
    return this.#emitReplacement(next, "history-redo");
  }

  replaceFromPersistence(input: unknown): Presentation {
    this.#document = parsePresentation(input);
    this.#past = [];
    this.#future = [];
    return this.document;
  }
}
