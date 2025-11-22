import { useEffect, useMemo, useRef, useState } from "react";

import { ControlPanel } from "@/components/ControlPanel";
import { Gallery } from "@/components/Gallery";
import { Hero } from "@/components/Hero";
import { TraitSelector } from "@/components/TraitSelector";
import { fetchLoras, generateImages, publishYokai } from "@/lib/api";
import { catalog, buildPrompt, type SelectionState } from "@/utils/promptBuilder";
import type { GenerationImage, LoraInfo, PublishMetadata } from "@/types";

const descriptorPresets = [
  { id: "moonfog", label: "月光と霧", prompt: "silver moon haze, drifting mist" },
  { id: "ink", label: "滲む墨", prompt: "bleeding ink edges, sumi-e grain" },
  { id: "storm", label: "雷雨", prompt: "distant thunder, wet cobblestones, electric air" },
  { id: "festival", label: "祭りの喧騒", prompt: "festival lanterns, muffled crowd, lingering incense" },
  { id: "relic", label: "古道具", prompt: "weathered relics, lacquer cracks, frayed silk cords" },
];

const defaultMeta: PublishMetadata = {
  title: "新しい妖怪",
  description: "",
  longitude: 139.76,
  latitude: 35.68,
  era: "now",
  color: "#f2c14e",
  scale: 1.0,
  source: "yokai-gen",
};

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
  const [extraNegatives, setExtraNegatives] = useState("");
  const [activeDescriptors, setActiveDescriptors] = useState<string[]>(["moonfog"]);
  const [steps, setSteps] = useState(28);
  const [cfg, setCfg] = useState(7.5);
  const [numImages, setNumImages] = useState(1);
  const [size, setSize] = useState(1024);
  const [seed, setSeed] = useState<number | null>(null);
  const [selectedLoras, setSelectedLoras] = useState<string[]>([]);
  const [images, setImages] = useState<GenerationImage[]>([]);
  const [selectedImage, setSelectedImage] = useState<GenerationImage | null>(null);
  const [metadata, setMetadata] = useState<PublishMetadata>(defaultMeta);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [publishStatus, setPublishStatus] = useState<string | null>(null);

  const loras = useLoras();

  const descriptorPrompts = useMemo(
    () =>
      descriptorPresets
        .filter((entry) => activeDescriptors.includes(entry.id))
        .map((entry) => entry.prompt),
    [activeDescriptors],
  );

  const extraNegList = useMemo(
    () =>
      extraNegatives
        .split(/[\n,]/)
        .map((entry) => entry.trim())
        .filter(Boolean),
    [extraNegatives],
  );

  const promptPreview = useMemo(
    () => buildPrompt({ selections, customPrompt, extraAdjectives: descriptorPrompts, extraNegatives: extraNegList }),
    [customPrompt, descriptorPrompts, extraNegList, selections],
  );

  const scrollToForm = () => formRef.current?.scrollIntoView({ behavior: "smooth" });

  const handleSelection = (categoryId: string, optionId: string) => {
    setSelections((prev) => ({ ...prev, [categoryId]: optionId || undefined }));
  };

  const toggleDescriptor = (id: string) => {
    setActiveDescriptors((prev) =>
      prev.includes(id) ? prev.filter((entry) => entry !== id) : [...prev, id],
    );
  };

  const handleToggleLora = (name: string) => {
    setSelectedLoras((prev) =>
      prev.includes(name) ? prev.filter((entry) => entry !== name) : [...prev, name],
    );
  };

  const handleGenerate = async () => {
    setError(null);
    setPublishStatus(null);
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
        seed: seed ?? undefined,
        width: size,
        height: size,
      };
      const response = await generateImages(payload);
      setImages(response.images);
      setSelectedImage(response.images[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedImage) {
      setPublishStatus("先に保存したい画像をギャラリーから選択してください。");
      return;
    }
    setPublishStatus("保存中…");
    try {
      const payload = {
        metadata: {
          ...metadata,
          era: metadata.era ?? "now",
          source: metadata.source ?? "yokai-gen",
        },
        image_base64: selectedImage.base64_png,
        prompt: promptPreview.prompt,
        negative_prompt: promptPreview.negative,
        seed: selectedImage.seed,
        lora: selectedImage.lora,
      };
      const res = await publishYokai(payload);
      setPublishStatus(`places.json に ${res.id} を保存しました (${res.image_url})`);
    } catch (err) {
      setPublishStatus(err instanceof Error ? err.message : "保存に失敗しました");
    }
  };

  const resetSelections = () => {
    setSelections({});
    setCustomPrompt("");
    setExtraNegatives("");
    setActiveDescriptors(["moonfog"]);
  };

  const updateMetadata = (key: keyof PublishMetadata, value: string | number | null) => {
    setMetadata((prev) => ({ ...prev, [key]: value as never }));
  };

  const randomizeLocation = () => {
    const lon = metadata.longitude ?? defaultMeta.longitude;
    const lat = metadata.latitude ?? defaultMeta.latitude;
    const jitter = () => (Math.random() - 0.5) * 0.02;
    setMetadata((prev) => ({ ...prev, longitude: lon + jitter(), latitude: lat + jitter() }));
  };

  return (
    <main className="app">
      <Hero onSurge={scrollToForm} />

      <section className="panel" ref={formRef}>
        <header className="panel__header">
          <div>
            <h2>プロンプト設計</h2>
            <p className="muted">物語の骨格を選び、足りない描写は自由に足していきましょう。</p>
          </div>
          <button className="ghost" onClick={resetSelections}>
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

        <div className="chips">
          {descriptorPresets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`chip ${activeDescriptors.includes(preset.id) ? "chip--active" : ""}`}
              onClick={() => toggleDescriptor(preset.id)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="stacked-inputs">
          <label className="custom-prompt">
            追加したい描写
            <textarea
              value={customPrompt}
              onChange={(event) => setCustomPrompt(event.target.value)}
              placeholder="例) blood moon reflection, folded paper charms"
            />
          </label>
          <label className="custom-prompt">
            追加ネガティブ
            <textarea
              value={extraNegatives}
              onChange={(event) => setExtraNegatives(event.target.value)}
              placeholder="例) low contrast, childlike, cartoon"
            />
          </label>
        </div>

        <div className="prompt-preview">
          <p className="muted">出力されるプロンプト</p>
          <p className="prompt-preview__text">{promptPreview.prompt}</p>
          <p className="muted">ネガティブ</p>
          <p className="prompt-preview__text">{promptPreview.negative}</p>
        </div>

        <button className="hero__cta" onClick={handleGenerate} disabled={loading}>
          {loading ? "生成中..." : "妖怪を生成"}
        </button>
        {error && <p className="error">{error}</p>}
      </section>

      <ControlPanel
        steps={steps}
        cfg={cfg}
        numImages={numImages}
        seed={seed}
        size={size}
        loras={loras}
        selectedLoras={selectedLoras}
        onStepsChange={setSteps}
        onCfgChange={setCfg}
        onNumImagesChange={setNumImages}
        onSeedChange={setSeed}
        onSizeChange={setSize}
        onToggleLora={handleToggleLora}
      />

      <section className="panel panel--publish">
        <header className="panel__header">
          <div>
            <h3>Cesium に保存</h3>
            <p className="muted">places.json と /img/yokai/ に書き出します。</p>
          </div>
          <span className="pill">{selectedImage ? `seed ${selectedImage.seed}` : "画像未選択"}</span>
        </header>

        <div className="panel__grid meta-grid">
          <label>
            タイトル
            <input
              type="text"
              value={metadata.title}
              onChange={(event) => updateMetadata("title", event.target.value)}
              placeholder="例) 赤鬼の物語"
            />
          </label>
          <label>
          経度 (lon)
          <input
            type="number"
            step="0.0001"
            value={metadata.longitude}
            onChange={(event) => {
              const value = event.target.value;
              updateMetadata("longitude", value === "" ? metadata.longitude : Number(value));
            }}
          />
        </label>
        <label>
          緯度 (lat)
          <input
            type="number"
            step="0.0001"
            value={metadata.latitude}
            onChange={(event) => {
              const value = event.target.value;
              updateMetadata("latitude", value === "" ? metadata.latitude : Number(value));
            }}
          />
        </label>
          <label>
            ピン色
            <input
              type="color"
              value={metadata.color}
              onChange={(event) => updateMetadata("color", event.target.value)}
            />
          </label>
          <label>
            スケール
            <input
            type="number"
            min="0.1"
            step="0.1"
            value={metadata.scale ?? 1}
            onChange={(event) => {
              const value = event.target.value;
              updateMetadata("scale", value === "" ? metadata.scale ?? 1 : Number(value));
            }}
          />
        </label>
          <label>
            時代タグ
            <select
              value={metadata.era}
              onChange={(event) => updateMetadata("era", event.target.value)}
            >
              <option value="now">現代（マップで強調）</option>
              <option value="past">過去・伝承</option>
            </select>
          </label>
        </div>

        <label className="custom-prompt">
          説明・あらすじ
          <textarea
            value={metadata.description ?? ""}
            onChange={(event) => updateMetadata("description", event.target.value)}
            placeholder="ロケーションや短い背景設定をメモしておくと後で便利です。"
          />
        </label>

        <div className="publish-actions">
          <div className="muted">
            <p>座標は後で手動で微調整しても OK / 乱数で少し散らすこともできます。</p>
            <button type="button" className="ghost ghost--small" onClick={randomizeLocation}>
              座標を少し散らす
            </button>
          </div>
          <button className="hero__cta" type="button" onClick={handlePublish} disabled={!selectedImage}>
            {selectedImage ? "places.json に書き出す" : "先に画像を選択"}
          </button>
        </div>

        {publishStatus && <p className="muted">{publishStatus}</p>}
      </section>

      <Gallery
        images={images}
        isLoading={loading}
        selectedSeed={selectedImage?.seed ?? null}
        onSelect={setSelectedImage}
      />
    </main>
  );
}
