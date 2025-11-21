import { useEffect, useMemo, useRef, useState } from "react";
import { Hero } from "@/components/Hero";
import { TraitSelector } from "@/components/TraitSelector";
import { ControlPanel } from "@/components/ControlPanel";
import { Gallery } from "@/components/Gallery";
import { catalog, buildPrompt, type SelectionState } from "@/utils/promptBuilder";
import { fetchLoras, generateImages } from "@/lib/api";
import type { GenerationImage, LoraInfo } from "@/types";

function useLoras() {
  const [loras, setLoras] = useState<LoraInfo[]>([]);

  useEffect(() => {
    fetchLoras()
      .then(setLoras)
      .catch(() => setLoras([]));
  }, []);

  return loras;
}

export default function App() {
  const formRef = useRef<HTMLDivElement>(null);
  const [selections, setSelections] = useState<SelectionState>({});
  const [customPrompt, setCustomPrompt] = useState("");
  const [steps, setSteps] = useState(28);
  const [cfg, setCfg] = useState(7.5);
  const [numImages, setNumImages] = useState(1);
  const [selectedLoras, setSelectedLoras] = useState<string[]>([]);
  const [images, setImages] = useState<GenerationImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loras = useLoras();

  const promptPreview = useMemo(
    () => buildPrompt({ selections, customPrompt }),
    [selections, customPrompt],
  );

  const scrollToForm = () => formRef.current?.scrollIntoView({ behavior: "smooth" });

  const handleSelection = (categoryId: string, optionId: string) => {
    setSelections((prev) => ({ ...prev, [categoryId]: optionId || undefined }));
  };

  const handleToggleLora = (name: string) => {
    setSelectedLoras((prev) =>
      prev.includes(name) ? prev.filter((entry) => entry !== name) : [...prev, name],
    );
  };

  const handleGenerate = async () => {
    setError(null);
    setLoading(true);
    try {
      const { prompt, negative } = promptPreview;
      const payload = {
        prompt,
        negative_prompt: negative,
        steps,
        guidance_scale: cfg,
        num_images: numImages,
        lora: selectedLoras,
      };
      const response = await generateImages(payload);
      setImages(response.images);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app">
      <Hero onSurge={scrollToForm} />

      <section className="panel" ref={formRef}>
        <header className="panel__header">
          <div>
            <h2>妖怪の特徴を選ぶ</h2>
            <p className="muted">分類・質感・雰囲気を組み合わせて、墨の指示書を作ります。</p>
          </div>
          <button className="ghost" onClick={() => setSelections({})}>
            リセット
          </button>
        </header>

        <div className="trait-grid">
          {catalog.categories.map((category) => (
            <TraitSelector
              key={category.id}
              category={category}
              value={selections[category.id]}
              onChange={handleSelection}
            />
          ))}
        </div>

        <label className="custom-prompt">
          追記 (任意)
          <textarea
            value={customPrompt}
            onChange={(event) => setCustomPrompt(event.target.value)}
            placeholder="例: blood moon reflection, folded paper charms"
          />
        </label>

        <div className="prompt-preview">
          <p className="muted">生成されるプロンプト:</p>
          <p>{promptPreview.prompt}</p>
          <p className="muted">ネガティブ:</p>
          <p>{promptPreview.negative}</p>
        </div>

        <button className="hero__cta" onClick={handleGenerate} disabled={loading}>
          {loading ? "召喚中..." : "妖怪を召喚する"}
        </button>
        {error && <p className="error">{error}</p>}
      </section>

      <ControlPanel
        steps={steps}
        cfg={cfg}
        numImages={numImages}
        loras={loras}
        selectedLoras={selectedLoras}
        onStepsChange={setSteps}
        onCfgChange={setCfg}
        onNumImagesChange={setNumImages}
        onToggleLora={handleToggleLora}
      />

      <Gallery images={images} isLoading={loading} />
    </main>
  );
}

