/**
 * PRISM Language Configuration
 * Supported: English and Hindi (+ Hinglish handled automatically)
 */

export const LANGUAGES = {
  en: {
    key: "en",
    name: "English",
    locale: "en-IN",
    greeting: "Hello! I'm PRISM, your AI assistant. How can I help you today? Please tell me what issue you are facing."
  },
  hi: {
    key: "hi",
    name: "Hindi",
    locale: "hi-IN",
    greeting: "Namaste! Main PRISM hoon, aapka AI assistant. Aaj main aapki kya madad kar sakta hoon? Apni problem batayein."
  },
}

export const DEFAULT_LANGUAGE = "en"

export function getLanguageConfig(key) {
  return LANGUAGES[key] || LANGUAGES[DEFAULT_LANGUAGE]
}
