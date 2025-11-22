import type { GenerationImage } from "@/types";

interface GalleryProps {
  images: GenerationImage[];
  isLoading: boolean;
  selectedSeed?: number | null;
  onSelect?: (image: GenerationImage) => void;
}

export function Gallery({ images, isLoading, selectedSeed, onSelect }: GalleryProps) {
  if (isLoading) {
    return (
      <section className="gallery gallery--loading">
        <p>生成中… 墨が乾くまで少しお待ちください。</p>
      </section>
    );
  }

  if (!images.length) {
    return (
      <section className="gallery gallery--empty">
        <p>まだ生成結果はありません。</p>
        <p className="muted">条件を選んで「妖怪を生成」を押すとここに並びます。</p>
      </section>
    );
  }

  return (
    <section className="gallery">
      {images.map((img) => {
        const isSelected = selectedSeed === img.seed;
        return (
          <article key={`${img.seed}-${img.base64_png.slice(0, 16)}`} className="gallery__card">
            <div className="gallery__frame">
              <img src={`data:image/png;base64,${img.base64_png}`} alt="Generated yokai" />
              {onSelect && (
                <button
                  type="button"
                  className={`gallery__select ${isSelected ? "gallery__select--active" : ""}`}
                  onClick={() => onSelect(img)}
                >
                  {isSelected ? "この絵を使う" : "選択する"}
                </button>
              )}
            </div>
            <footer>
              <span>seed {img.seed}</span>
              <span>{img.width}x{img.height}px</span>
              {img.lora.length > 0 && <span>LoRA: {img.lora.join(", ")}</span>}
            </footer>
          </article>
        );
      })}
    </section>
  );
}
