import { getLanguageConfig } from '../config/languages'

/**
 * Modular TTS Manager Abstraction for PRISM Support System.
 * Abstracts speech synthesis providers and browser fallbacks.
 * Ensures TTS failures NEVER break Agora sessions or caller UX.
 *
 * ROOT CAUSE OF MULTILINGUAL BUG:
 * speechSynthesis.getVoices() returns an empty array [] on first call
 * in most browsers (Chrome, Edge). Voices are loaded asynchronously and
 * only available after the 'voiceschanged' event fires.
 * Without pre-loading, ALL language selections fell back to the browser's
 * default English voice despite the greeting TEXT being correctly localized.
 *
 * FIX: Pre-warm voices on module load via voiceschanged event.
 * Then voice matching is guaranteed to run against the real voice list.
 */

// ─── Voice pre-warming ───────────────────────────────────────────────────────
// Start loading voices immediately when this module is imported.
// This ensures voices are available before the first speak() call.
let cachedVoices = []
let voicesReady = false

function loadVoices() {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
  const v = window.speechSynthesis.getVoices()
  if (v && v.length > 0) {
    cachedVoices = v
    voicesReady = true
  }
}

if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  // Load synchronously in case already available (Firefox, Safari)
  loadVoices()
  // Also listen for the async event (Chrome, Edge)
  window.speechSynthesis.addEventListener('voiceschanged', () => {
    loadVoices()
  })
}

/**
 * Get best matching voice for a given locale.
 * Priority: exact locale match → language-prefix match → null (use browser default)
 * NEVER silently falls back to English if the correct language voice exists.
 */
function findVoice(locale) {
  const voices = cachedVoices
  if (!voices || voices.length === 0) return null

  const localeLower = locale.toLowerCase()
  const langCode = localeLower.split('-')[0]

  // 1. Exact locale match (e.g. "hi-IN" === "hi-IN")
  let match = voices.find(v => v.lang.toLowerCase() === localeLower)
  if (match) return match

  // 2. Language-prefix match (e.g. "bn" starts "bn-BD", "bn-IN")
  match = voices.find(v => v.lang.toLowerCase().startsWith(langCode + '-'))
  if (match) return match

  // 3. Plain language code match (rare but exists on some OS)
  match = voices.find(v => v.lang.toLowerCase() === langCode)
  if (match) return match

  return null
}

// ─── TTSManager ─────────────────────────────────────────────────────────────

class TTSManager {
  constructor() {
    this.isSpeaking = false
    this.activeUtterance = null
  }

  cancel() {
    this.isSpeaking = false
    this.activeUtterance = null
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel()
      } catch (e) {
        console.warn('[PRISM TTS] Cancel warning:', e)
      }
    }
  }

  /**
   * Speak localized text in the specified language.
   *
   * @param {string} text      - The ALREADY LOCALIZED greeting text (not English)
   * @param {string} langKey   - Language key (e.g. "hi", "bn", "ta")
   * @param {Object} callbacks - { onStart, onEnd, onError }
   *
   * IMPORTANT: text must already be in the target language.
   * Setting lang on the utterance does NOT translate English text.
   */
  async speak(text, langKey = 'en', callbacks = {}) {
    this.cancel()

    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      console.warn('[PRISM TTS] SpeechSynthesis API unavailable in this browser')
      callbacks.onEnd?.()
      return { success: false, reason: 'unsupported' }
    }

    const config = getLanguageConfig(langKey)
    const textToSpeak = text || config.greeting

    // Wait for voices to be available (fixes Chrome/Edge async loading race)
    const voices = await this._getVoicesReady()
    const matchedVoice = findVoice(config.locale)

    // ── Development diagnostic logging ──────────────────────────────────
    console.group(`[PRISM TTS] Language: ${config.name}`)
    console.log('  locale      :', config.locale)
    console.log('  text        :', textToSpeak.substring(0, 60) + (textToSpeak.length > 60 ? '…' : ''))
    console.log('  voices total:', voices.length)
    if (matchedVoice) {
      console.log('  selectedVoice :', matchedVoice.name)
      console.log('  voiceLocale   :', matchedVoice.lang)
      console.log('  voiceURI      :', matchedVoice.voiceURI)
    } else {
      console.warn('  selectedVoice : ❌ NO MATCHING VOICE FOUND for', config.locale)
      console.warn('  Available voices:', voices.map(v => `${v.lang} (${v.name})`).join(', '))
      console.warn('  ⚠ Browser will use its default voice — audio may not be in the selected language.')
    }
    console.groupEnd()
    // ────────────────────────────────────────────────────────────────────

    try {
      const utterance = new SpeechSynthesisUtterance(textToSpeak)
      utterance.lang = config.locale
      utterance.rate = 0.92
      utterance.pitch = 1

      if (matchedVoice) {
        utterance.voice = matchedVoice
      }
      // If no matching voice: utterance.voice is left unset.
      // The browser's default voice will be used. The text is still
      // correctly localized — the audio quality/accent depends on available voices.

      this.activeUtterance = utterance
      this.isSpeaking = true

      return new Promise((resolve) => {
        utterance.onstart = () => {
          this.isSpeaking = true
          callbacks.onStart?.()
        }

        utterance.onend = () => {
          this.isSpeaking = false
          callbacks.onEnd?.()
          resolve({ success: true, voiceUsed: matchedVoice?.name || 'browser-default' })
        }

        utterance.onerror = (err) => {
          console.warn('[PRISM TTS] SpeechSynthesis error:', err.error, 'for lang:', config.locale)
          this.isSpeaking = false
          callbacks.onError?.(err)
          callbacks.onEnd?.()
          resolve({ success: false, error: err })
        }

        try {
          window.speechSynthesis.speak(utterance)
        } catch (err) {
          console.warn('[PRISM TTS] speak() invocation failed:', err)
          this.isSpeaking = false
          callbacks.onEnd?.()
          resolve({ success: false, error: err })
        }
      })
    } catch (err) {
      console.warn('[PRISM TTS] Unexpected exception:', err)
      this.isSpeaking = false
      callbacks.onEnd?.()
      return { success: false, error: err }
    }
  }

  /**
   * Wait up to 1000ms for voices to be available.
   * Solves Chrome/Edge async voiceschanged race condition.
   */
  _getVoicesReady() {
    return new Promise((resolve) => {
      if (voicesReady || cachedVoices.length > 0) {
        resolve(cachedVoices)
        return
      }
      // Poll up to 1000ms in 50ms intervals
      let waited = 0
      const interval = setInterval(() => {
        loadVoices()
        waited += 50
        if (cachedVoices.length > 0 || waited >= 1000) {
          clearInterval(interval)
          resolve(cachedVoices)
        }
      }, 50)
    })
  }

  /**
   * Returns a report of voice coverage for all supported locales.
   * Call this in the browser console: ttsManager.diagnose()
   */
  async diagnose() {
    const { LANGUAGES } = await import('../config/languages')
    await this._getVoicesReady()
    const results = {}
    for (const [key, lang] of Object.entries(LANGUAGES)) {
      const voice = findVoice(lang.locale)
      results[key] = {
        name: lang.name,
        locale: lang.locale,
        voiceFound: !!voice,
        voiceName: voice?.name || null,
        voiceLang: voice?.lang || null,
        greetingPreview: lang.greeting.substring(0, 40) + '…',
      }
    }
    console.table(results)
    return results
  }
}

export const ttsManager = new TTSManager()

// Expose diagnose() to browser console for debugging
if (typeof window !== 'undefined') {
  window.__prismTTSDiagnose = () => ttsManager.diagnose()
  console.info('[PRISM TTS] Run window.__prismTTSDiagnose() to see voice coverage for all languages.')
}
