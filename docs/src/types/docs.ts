export type Locale = 'vi' | 'en'

export type Localized = Record<Locale, string>

export type LocalizedList = Record<Locale, string[]>

export type DocSection = {
  id: string
  title: Localized
  summary?: Localized
  bullets?: LocalizedList
  code?: string
}
