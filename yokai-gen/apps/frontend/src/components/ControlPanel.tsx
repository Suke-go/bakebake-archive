import type { LoraInfo } from "@/types";

interface ControlPanelProps {
  steps: number;
  cfg: number;
  numImages: number;
  loras: LoraInfo[];
  selectedLoras: string[];
  onStepsChange: (value: number) => void;
  onCfgChange: (value: number) => void;
  onNumImagesChange: (value: number) => void;
  onToggleLora: (name: string) => void;
}

export function ControlPanel({
  steps,
  cfg,
  numImages,
  loras,
  selectedLoras,
  onStepsChange,
  onCfgChange,
  onNumImagesChange,
  onToggleLora,
}: ControlPanelProps) {
  return (
    <section className="panel">
      <h3>生成パラメータ</h3>
      <div className="panel__grid">
        <label>
          ステップ
          <input
            type="range"
            min={12}
            max={60}
            value={steps}
            onChange={(event) => onStepsChange(Number(event.target.value))}
          />
          <span>{steps}</span>
        </label>
        <label>
          CFG
          <input
            type="range"
            min={3}
            max={12}
            step={0.5}
            value={cfg}
            onChange={(event) => onCfgChange(Number(event.target.value))}
          />
          <span>{cfg.toFixed(1)}</span>
        </label>
        <label>
          枚数
          <input
            type="range"
            min={1}
            max={3}
            value={numImages}
            onChange={(event) => onNumImagesChange(Number(event.target.value))}
          />
          <span>{numImages}</span>
        </label>
      </div>

      <div className="panel__lora">
        <h4>LoRA</h4>
        {loras.length === 0 && <p className="muted">`models/lora` に LoRA を配置してください。</p>}
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

