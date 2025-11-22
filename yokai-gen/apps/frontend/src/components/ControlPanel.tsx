import type { LoraInfo } from "@/types";

interface ControlPanelProps {
  steps: number;
  cfg: number;
  numImages: number;
  seed: number | null;
  size: number;
  loras: LoraInfo[];
  selectedLoras: string[];
  onStepsChange: (value: number) => void;
  onCfgChange: (value: number) => void;
  onNumImagesChange: (value: number) => void;
  onSeedChange: (value: number | null) => void;
  onSizeChange: (value: number) => void;
  onToggleLora: (name: string) => void;
}

const SIZE_PRESETS = [
  { label: "768px", value: 768 },
  { label: "896px", value: 896 },
  { label: "1024px", value: 1024 },
];

export function ControlPanel({
  steps,
  cfg,
  numImages,
  seed,
  size,
  loras,
  selectedLoras,
  onStepsChange,
  onCfgChange,
  onNumImagesChange,
  onSeedChange,
  onSizeChange,
  onToggleLora,
}: ControlPanelProps) {
  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h3>生成パラメータ</h3>
          <p className="muted">LoRA / サイズ / シードなど微調整できます。</p>
        </div>
      </header>

      <div className="panel__grid panel__grid--compact">
        <label>
          ステップ
          <div className="slider-row">
            <input
              type="range"
              min={12}
              max={60}
              value={steps}
              onChange={(event) => onStepsChange(Number(event.target.value))}
            />
            <span className="slider-value">{steps}</span>
          </div>
        </label>
        <label>
          CFG
          <div className="slider-row">
            <input
              type="range"
              min={3}
              max={12}
              step={0.5}
              value={cfg}
              onChange={(event) => onCfgChange(Number(event.target.value))}
            />
            <span className="slider-value">{cfg.toFixed(1)}</span>
          </div>
        </label>
        <label>
          枚数
          <div className="slider-row">
            <input
              type="range"
              min={1}
              max={4}
              value={numImages}
              onChange={(event) => onNumImagesChange(Number(event.target.value))}
            />
            <span className="slider-value">{numImages}</span>
          </div>
        </label>
        <label>
          シード
          <div className="input-pill">
            <input
              type="number"
              placeholder="ランダム"
              value={seed ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                onSeedChange(value === "" ? null : Number(value));
              }}
            />
            <button type="button" onClick={() => onSeedChange(Math.floor(Math.random() * 10_000_000))}>
              🎲
            </button>
          </div>
        </label>
        <label>
          出力サイズ
          <select value={size} onChange={(event) => onSizeChange(Number(event.target.value))}>
            {SIZE_PRESETS.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {preset.label}（正方形）
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="panel__lora">
        <h4>LoRA</h4>
        {loras.length === 0 && (
          <p className="muted">`models/lora` に LoRA を置くとここに一覧表示されます。</p>
        )}
        <ul>
          {loras.map((lora) => (
            <li key={lora.name}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedLoras.includes(lora.name)}
                  onChange={() => onToggleLora(lora.name)}
                />
                {lora.name}
              </label>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
