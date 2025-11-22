import "./Hero.css";

interface HeroProps {
  onSurge?: () => void;
}

export function Hero({ onSurge }: HeroProps) {
  return (
    <section className="hero">
      <div className="hero__content">
        <p className="hero__eyebrow">Yokai Generator</p>
        <h1>
          記憶の墨を<span>滲ませ</span>、妖怪を呼び起こす
        </h1>
        <p className="hero__body">
          舞台・質感・雰囲気を選び、好みの言葉を継ぎ足していくだけ。
          生成した妖怪はワンクリックで Cesium の地図に保存できます。
        </p>
        <button className="hero__cta" onClick={onSurge}>
          生成パネルへ進む
        </button>
      </div>
      <div className="hero__glow" aria-hidden="true" />
    </section>
  );
}
