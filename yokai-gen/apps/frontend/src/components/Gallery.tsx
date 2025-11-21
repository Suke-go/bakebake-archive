import type { GenerationImage } from "@/types";

interface GalleryProps {
  images: GenerationImage[];
  isLoading: boolean;
}

export function Gallery({ images, isLoading }: GalleryProps) {
  if (isLoading) {
    return (
      <section className="gallery gallery--loading">
        <p>霧が立ちこめています… (生成中)</p>
      </section>
    );
  }

  if (!images.length) {
    return (
      <section className="gallery gallery--empty">
        <p>まだ妖怪は現れていません。</p>
        <p className="muted">特徴を選び「妖怪を召喚する」を押してください。</p>
      </section>
    );
  }

  return (
    <section className="gallery">
      {images.map((img) => (
        <article key={`${img.seed}-${img.base64_png.slice(0, 16)}`} className="gallery__card">
          <img src={`data:image/png;base64,${img.base64_png}`} alt="Generated yokai" />
          <footer>
            <span>seed {img.seed}</span>
            {img.lora.length > 0 && <span>LoRA: {img.lora.join(", ")}</span>}
          </footer>
        </article>
      ))}
    </section>
  );
}

