/* Mock data shared across views */

const OCR_ENGINES = [
  { id: "tesseract", name: "Tesseract 5", type: "Local · CLI", status: "online", detail: "fra+lat installed · v5.3.4" },
  { id: "pero", name: "Pero OCR", type: "Local · Python", status: "online", detail: "checkpoint: parzival-base" },
  { id: "kraken", name: "Kraken HTR", type: "Local · Python", status: "online", detail: "model: catmus-medieval-1.5" },
  { id: "calamari", name: "Calamari OCR", type: "Local · Python", status: "offline", detail: "checkpoint missing" },
  { id: "mistral_ocr", name: "Mistral OCR", type: "Cloud API", status: "online", detail: "MISTRAL_API_KEY ✓" },
  { id: "google_vision", name: "Google Vision", type: "Cloud API", status: "online", detail: "service account ✓" },
  { id: "azure", name: "Azure Doc Intel", type: "Cloud API", status: "offline", detail: "endpoint not set" },
];

const LLM_PROVIDERS = [
  { id: "openai", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], status: "online" },
  { id: "anthropic", name: "Anthropic", models: ["claude-opus-4", "claude-sonnet-4.5", "claude-haiku-4.5"], status: "online" },
  { id: "mistral", name: "Mistral", models: ["mistral-large-2", "pixtral-large"], status: "online" },
  { id: "ollama", name: "Ollama", models: ["llama3.2:8b", "qwen2.5:14b"], status: "offline" },
];

const NORM_PROFILES = [
  "nfc",
  "caseless",
  "minimal",
  "medieval_french",
  "early_modern_french",
  "medieval_latin",
  "medieval_english",
  "early_modern_english",
  "secretary_hand",
  "sans_ponctuation",
  "sans_apostrophes",
];

const HTR_CORPORA = [
  { name: "CATMuS-Medieval", desc: "Medieval Latin & vernacular manuscripts, 11th–15th c.", lang: "lat, fro, en", script: "Caroline, Gothic", pages: 2480, license: "CC-BY-4.0" },
  { name: "HTR-Lorrain", desc: "Notarial registers from Lorraine, 16th–18th c.", lang: "fre", script: "Cursive moderne", pages: 940, license: "CC0" },
  { name: "Esposalles", desc: "Marriage records of Barcelona Cathedral, 17th c.", lang: "spa, lat", script: "Procesal", pages: 173, license: "CC-BY-NC" },
  { name: "Gallica-Press-1900", desc: "Printed press, BnF Gallica selection, 1880–1920.", lang: "fre", script: "Modern print", pages: 12340, license: "Open" },
];

const HF_DATASETS = [
  { name: "IAM-Handwriting-DB", desc: "English handwritten lines from forms, ICDAR classic baseline.", downloads: "184K", likes: 320, tags: ["ocr", "handwriting", "en"] },
  { name: "RIMES-2011", desc: "Handwritten French letters, structured layout, train/val/test.", downloads: "62K", likes: 142, tags: ["htr", "fr", "letters"] },
  { name: "BnF-Gallica-OCR", desc: "Curated OCR pairs from Gallica, mixed quality, 19th–20th c.", downloads: "12K", likes: 88, tags: ["ocr", "fr", "historical"] },
  { name: "Bullinger-Briefwechsel", desc: "Heinrich Bullinger correspondence, 16th c. Reformed Latin.", downloads: "3.4K", likes: 41, tags: ["htr", "lat", "16c"] },
];

const REPORTS = [
  { name: "rapport_2026_05_18_tesseract_vs_mistral.html", date: "18 mai 2026 · 14:32", engines: 3, docs: 240, best: { engine: "Mistral OCR", cer: 4.8 }, size: "12.4 MB" },
  { name: "edition_critique_glose_psaumes.html", date: "12 mai 2026 · 09:11", engines: 5, docs: 88, best: { engine: "Pero→Claude", cer: 2.1 }, size: "8.1 MB" },
  { name: "press_1900_robustness.html", date: "05 mai 2026 · 22:04", engines: 4, docs: 1240, best: { engine: "Tesseract", cer: 7.3 }, size: "34.0 MB" },
  { name: "demo_synthetic.html", date: "01 mai 2026 · 18:00", engines: 2, docs: 12, best: { engine: "—", cer: 0.0 }, size: "0.6 MB" },
];

const RESULTS = [
  { rank: 1, engine: "Mistral OCR", model: "mistral-ocr-2410", cer: 4.82, wer: 11.4, speed: "1.2s/page", cost: "$0.041", color: "green" },
  { rank: 2, engine: "Pero → Claude", model: "claude-sonnet-4.5", cer: 5.17, wer: 12.1, speed: "3.8s/page", cost: "$0.038", color: "blue" },
  { rank: 3, engine: "Tesseract → GPT-4o", model: "gpt-4o", cer: 6.04, wer: 14.7, speed: "2.1s/page", cost: "$0.029", color: "ink" },
  { rank: 4, engine: "Tesseract 5", model: "fra+lat", cer: 9.86, wer: 22.4, speed: "0.4s/page", cost: "$0.000", color: "ink" },
  { rank: 5, engine: "Kraken HTR", model: "catmus-medieval", cer: 11.2, wer: 25.9, speed: "0.9s/page", cost: "$0.000", color: "ink" },
];

const LOG_LINES = [
  { ts: "14:32:01", lvl: "info", text: "[runner] starting benchmark — corpus=corpus_psaumes_240/ engines=5 norm=medieval_latin" },
  { ts: "14:32:02", lvl: "blue", text: "[corpus] discovered 240 pages, 240 ground truth files (text), 0 unmatched" },
  { ts: "14:32:03", lvl: "info", text: "[engine:tesseract] init ok — lang=fra+lat psm=3" },
  { ts: "14:32:04", lvl: "info", text: "[engine:pero] init ok — checkpoint=parzival-base" },
  { ts: "14:32:05", lvl: "warn", text: "[engine:calamari] checkpoint missing, skipping" },
  { ts: "14:32:06", lvl: "info", text: "[engine:mistral_ocr] init ok — model=mistral-ocr-2410" },
  { ts: "14:32:09", lvl: "ok", text: "[runner] page 001/240 — tesseract done in 0.41s" },
  { ts: "14:32:11", lvl: "ok", text: "[runner] page 001/240 — pero done in 0.92s" },
  { ts: "14:32:13", lvl: "ok", text: "[runner] page 001/240 — mistral_ocr done in 1.21s" },
  { ts: "14:32:16", lvl: "blue", text: "[pipeline] pero → claude-sonnet-4.5 — post-correction page 001/240" },
];

const SYNTHESIS_SENTENCES = [
  "Sur 240 pages de psautiers glosés (latin médiéval, écriture caroline), Mistral OCR atteint le meilleur CER (4.82 %) — devant la chaîne Pero → Claude (5.17 %).",
  "L'écart entre les deux premiers est inférieur à l'intervalle de confiance bootstrap à 95 % : non-significatif (p = 0.18, test de Friedman + Nemenyi).",
  "Tesseract reste compétitif sur la vitesse (0.4 s/page) avec un CER honorable (9.86 %) — option Pareto-optimale si le coût compte.",
  "Aucune sur-normalisation détectée chez la chaîne Pero → Claude : 0 modernisation silencieuse d'orthographe historique sur l'échantillon.",
];

window.PicaData = {
  OCR_ENGINES, LLM_PROVIDERS, NORM_PROFILES,
  HTR_CORPORA, HF_DATASETS, REPORTS, RESULTS,
  LOG_LINES, SYNTHESIS_SENTENCES,
};
