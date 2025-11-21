import type { TraitCategory } from "@/utils/promptBuilder";

interface TraitSelectorProps {
  category: TraitCategory;
  value?: string;
  onChange: (id: string, value: string) => void;
}

export function TraitSelector({ category, value, onChange }: TraitSelectorProps) {
  return (
    <label className="trait-selector">
      <span>{category.label}</span>
      <select
        value={value ?? ""}
        onChange={(event) => onChange(category.id, event.target.value)}
      >
        <option value="">未選択</option>
        {category.options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

