/**
 * PRISM Language Configuration
 * Supported: English and Hindi (+ Hinglish handled automatically)
 */

export const LANGUAGES = {
  en: {
    key: "en",
    name: "English",
    locale: "en-IN",
    greeting: "Hello, this is PRISM, your AI support assistant. Please describe your problem and I'll help you resolve it."
  },
  hi: {
    key: "hi",
    name: "Hindi",
    locale: "hi-IN",
    greeting: "Namaste! Main PRISM hoon, aapka AI support assistant. Apni problem batayein, main help karunga."
  },
}

export const DEFAULT_LANGUAGE = "en"

export function getLanguageConfig(key) {
  return LANGUAGES[key] || LANGUAGES[DEFAULT_LANGUAGE]
}
