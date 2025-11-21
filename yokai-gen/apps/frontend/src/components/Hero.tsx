import "./Hero.css";

interface HeroProps {
  onSurge?: () => void;
}

export function Hero({ onSurge }: HeroProps) {
  return (
    <section className="hero">
      <div className="hero__content">
        <p className="hero__eyebrow">妖怪生成アトリエ</p>
        <h1>
          墨の闇から <span>妖し</span> を呼び覚ます
        </h1>
        <p className="hero__body">
          江戸の夜気、濡れた石畳、微かな灯火。特徴を選ぶだけで、水木しげるの画帳をめくるように妖怪が現れます。
        </p>
        <button className="hero__cta" onClick={onSurge}>
          妖怪を召喚する
        </button>
      </div>
      <div className="hero__glow" aria-hidden="true" />
    </section>
  );
}

