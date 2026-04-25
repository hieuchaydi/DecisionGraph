import { HERO_CHIPS, HERO_TEXT } from '../content/docsContent'
import type { Locale } from '../types/docs'

type HeroCardProps = {
  locale: Locale
}

export function HeroCard({ locale }: HeroCardProps) {
  return (
    <section className="hero card">
      <h2>{HERO_TEXT[locale].title}</h2>
      <p className="summary">{HERO_TEXT[locale].subtitle}</p>
      <div className="chips">
        {HERO_CHIPS[locale].map((chip) => (
          <span key={chip}>{chip}</span>
        ))}
      </div>
    </section>
  )
}
