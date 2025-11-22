import traitsData from "@/data/yokai_traits.json";

export interface TraitOption {
  id: string;
  label: string;
  prompt: string;
  negatives?: string[];
}

export interface TraitCategory {
  id: string;
  label: string;
  options: TraitOption[];
}

export interface TraitsCatalog {
  defaultNegative: string;
  categories: TraitCategory[];
}

export type SelectionState = Record<string, string | undefined>;

export interface PromptBuildInput {
  selections: SelectionState;
  customPrompt?: string;
  extraAdjectives?: string[];
  extraNegatives?: string[];
}

export interface PromptBuildResult {
  prompt: string;
  negative: string;
}

export const catalog = traitsData as TraitsCatalog;

export function buildPrompt(input: PromptBuildInput): PromptBuildResult {
  const pieces: string[] = ["masterpiece", "yokai style", "ink wash lighting"];
  const negatives: string[] = [];

  for (const category of catalog.categories) {
    const selectedId = input.selections[category.id];
    if (!selectedId) continue;
    const option = category.options.find((opt) => opt.id === selectedId);
    if (!option) continue;
    pieces.push(option.prompt);
    if (option.negatives) {
      negatives.push(...option.negatives);
    }
  }

  if (input.extraAdjectives?.length) {
    pieces.push(...input.extraAdjectives);
  }

  if (input.customPrompt?.trim()) {
    pieces.push(input.customPrompt.trim());
  }

  if (input.extraNegatives?.length) {
    negatives.push(
      ...input.extraNegatives
        .map((entry) => entry.trim())
        .filter((entry) => entry.length > 0),
    );
  }

  const prompt = pieces.join(", ");
  const negative = [catalog.defaultNegative, ...negatives].filter(Boolean).join(", ");
  return { prompt, negative };
}

