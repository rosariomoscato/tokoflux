import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowRightLeft, ChartNoAxesCombined, Check, ChevronDown, Code2, Copy, Cpu, FlaskConical, Gauge, HelpCircle, History, Languages, Monitor, Play, Power, Radio, RotateCcw, Timer, Trash2, Trophy, X, Zap } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "./button";
import "./style.css";

const VERSION = "0.1.1";
const AUTHOR_URL = "https://rosmoscato.xyz";
const COLORS = ["var(--plot)", "var(--cyan)"];
const DEFAULT_CONTEXT = 8192;
const CONTEXT_OPTIONS = [2048, 4096, 8192, 16384, 32768];

const strings = {
  it: {
    sub: "Monitor dell’inferenza locale", theme: "Tema", lang: "Lingua", system: "Sistema", light: "Chiaro", dark: "Scuro",
    online: "Ollama connesso", offline: "Ollama non raggiungibile", connecting: "Connessione a Ollama",
    title: "Monitor", desc: "Misura come rispondono i modelli AI sul tuo computer.", latest: "Ultima prova",
    decode: "Velocità di generazione", prompt: "Lettura del prompt", first: "Tempo al primo token", total: "Tempo totale",
    hardware: "Modelli attivi", noActive: "Nessun modello caricato.", context: "Contesto", gpu: "Quota del modello sulla GPU",
    memory: "Memoria del modello", usage: "Quota di memoria, distinta dal carico istantaneo della GPU.",
    benchmark: "Benchmark", benchmarkDesc: "Stesso prompt, fino a due modelli.",
    modelA: "Primo modello", modelB: "Secondo modello", none: "Nessuno", mode: "Caricamento",
    warm: "A caldo", cold: "A freddo", start: "Esegui prova", running: "Prova in corso",
    warmHelp: "Precarica il modello prima della misura. Ollama può riusare i token in cache.",
    coldHelp: "Scarica dalla memoria ogni modello selezionato prima della relativa prova.",
    done: "Prova completata", error: "Prova interrotta. Controlla che Ollama sia attivo e riprova.",
    history: "Storico", empty: "Esegui la prima prova per vedere i risultati.", trend: "Andamento generazione",
    comparison: "Confronto", date: "Data", model: "Modello", load: "Caricamento", cached: "Token del prompt in cache",
    tokens: "token", units: "tok/s", failed: "Impossibile leggere i dati del Monitor.",
    limit: "Limite di generazione raggiunto", noModels: "Nessun modello disponibile",
    spread: "min–max", repeats: "{n} ripetizioni",
    help: "Guida", helpTitle: "Guida", close: "Chiudi",
    howToStart: "Come iniziare",
    howToStartText: "Avvia Ollama e lascialo aperto. Apri Tokoflux con Avvia-Tokoflux.cmd. In Benchmark scegli uno o due modelli, seleziona «A caldo» o «A freddo» e premi «Esegui prova». I risultati si salvano automaticamente in SQLite.",
    warmCold: "A caldo e a freddo",
    warmColdText: "«A caldo» precarica il modello prima di avviare il cronometro: misuri la generazione con il modello già in memoria (Ollama può riusare i token in cache). «A freddo» scarica il modello dalla memoria prima della prova: il tempo include il caricamento dal disco, anche se la cache del sistema operativo può conservare dati dell’SSD.",
    whatPrompt: "Cosa chiede il prompt",
    whatPromptText: "Il prompt chiede a ogni modello di scrivere una funzione Python che unisce intervalli chiusi sovrapposti senza modificare l’input, con quattro casi di test unittest (input vuoto, intervalli non ordinati, estremi che si toccano, intervalli separati). Il testo resta in inglese.",
    testsNote: "I test generati non vengono eseguiti: Tokoflux misura solo la generazione del codice e delle metriche.",
    readMetrics: "Come leggere le metriche",
    readMetricsList: [
      "Velocità di generazione (tok/s): token prodotti al secondo.",
      "Lettura del prompt (tok/s): velocità con cui il modello elabora il prompt.",
      "Tempo al primo token: primo frammento di risposta o ragionamento ricevuto in streaming.",
      "Tempo totale: misurato dal server Tokoflux.",
      "Quota del modello sulla GPU: memoria del modello allocata sulla GPU secondo Ollama. «100% GPU» indica dove è caricato il modello, non il carico della GPU.",
      "Mediana e ripetizioni: ogni prova ripete la misura (predefinito 3) e mostra la mediana con l’intervallo min–max.",
    ],
    exactPrompt: "Prompt esatto", promptLangNote: "Il testo resta in inglese in entrambe le lingue.",
    copy: "Copia", copied: "Copiato",
    credits: "Versione e crediti", creditsTech: "Tecnologie",
    showPrompt: "Mostra il prompt", hidePrompt: "Nascondi il prompt",
    compareBtn: "Confronta", compareOff: "Chiudi confronto", selectModel: "Seleziona modello",
    genShort: "Velocità", promptShort: "Prompt", firstShort: "1° token", totalShort: "Totale", loadShort: "Carico",
    winner: "Vince", tie: "Pareggio", ofMetrics: "metriche",
    clearHistory: "Pulisci storico", clearHistoryConfirm: "Eliminare tutti i risultati?",
    resetApp: "Resetta app", resetAppConfirm: "Ripristinare l’app (storico e preferenze)?",
    yesClear: "Sì, elimina", yesReset: "Sì, ripristina", cancel: "Annulla",
    cleared: "Storico cancellato",
    shutdown: "Spegni", shutdownConfirm: "Arrestare Tokoflux?", yesShutdown: "Sì, arresta",
    stopped: "Tokoflux arrestato", stoppedHint: "Puoi chiudere questa scheda.",
    contextLabel: "Contesto", gpuBudget: "Memoria GPU (GiB)",
    combinedSize: "I due modelli insieme: ≈ {n} GiB.",
    vramWarning: "Oltre la soglia memoria GPU ({n} GiB). Riduci il contesto o usa un modello alla volta per evitare errori ROCm.",
    rocmTitle: "Memoria GPU ed errori ROCm",
    rocmList: [
      "Scegli un contesto più piccolo (es. 2.048 o 4.096) per ridurre la memoria usata dal modello. Il valore predefinito è 8.192.",
      "La soglia «Memoria GPU» avvisa quando due modelli insieme superano la memoria che vuoi lasciare alla GPU.",
      "Per limitare i layer sulla GPU, avvia Ollama con OLLAMA_NUM_GPU (es. 24) o fissa un tetto alla VRAM con OLLAMA_MAX_VRAM (es. 16).",
      "Dopo aver cambiato queste variabili, riavvia Ollama. Su iGPU AMD (Strix Halo) il backend Vulkan può risultare più stabile di ROCm.",
    ],
    claim: "handcrafted by a human, upgraded by agents",
  },
  en: {
    sub: "Local inference monitor", theme: "Theme", lang: "Language", system: "System", light: "Light", dark: "Dark",
    online: "Ollama connected", offline: "Ollama unavailable", connecting: "Connecting to Ollama",
    title: "Monitor", desc: "Measure how AI models respond on your computer.", latest: "Latest run",
    decode: "Generation speed", prompt: "Prompt processing", first: "Time to first token", total: "Total time",
    hardware: "Active models", noActive: "No model loaded.", context: "Context", gpu: "Model share on GPU",
    memory: "Model memory", usage: "Share of model memory, separate from current GPU utilization.",
    benchmark: "Benchmark", benchmarkDesc: "One prompt, up to two models.",
    modelA: "First model", modelB: "Second model", none: "None", mode: "Loading mode",
    warm: "Warm", cold: "Cold", start: "Run benchmark", running: "Benchmark running",
    warmHelp: "Preloads the model before timing. Ollama may reuse cached tokens.",
    coldHelp: "Unloads each selected model from memory before its run.",
    done: "Benchmark complete", error: "Benchmark interrupted. Check that Ollama is running and try again.",
    history: "History", empty: "Run a benchmark to see results here.", trend: "Generation trend",
    comparison: "Comparison", date: "Date", model: "Model", load: "Load time", cached: "Cached prompt tokens",
    tokens: "tokens", units: "tok/s", failed: "Could not read monitor data.",
    limit: "Generation limit reached", noModels: "No model available",
    spread: "min–max", repeats: "{n} runs",
    help: "Help", helpTitle: "Help", close: "Close",
    howToStart: "Getting started",
    howToStartText: "Start Ollama and keep it open. Open Tokoflux with Avvia-Tokoflux.cmd. In Benchmark choose one or two models, pick Warm or Cold, then press Run benchmark. Results are saved automatically to SQLite.",
    warmCold: "Warm vs cold",
    warmColdText: "Warm preloads the model before timing: you measure generation with the model already in memory (Ollama may reuse cached tokens). Cold unloads the model from memory first: the time includes loading from disk, though the OS cache may still keep SSD data.",
    whatPrompt: "What the prompt asks",
    whatPromptText: "The prompt asks each model to write a Python function that merges closed overlapping intervals without mutating its input, with four unittest cases (empty input, unsorted intervals, touching endpoints, separate intervals). The text stays in English.",
    testsNote: "Generated tests are not executed: Tokoflux only measures code generation and metrics.",
    readMetrics: "How to read the metrics",
    readMetricsList: [
      "Generation speed (tok/s): tokens produced per second.",
      "Prompt processing (tok/s): how fast the model processes the prompt.",
      "Time to first token: first response or reasoning chunk received in streaming.",
      "Total time: measured by the Tokoflux server.",
      'Model share on GPU: model memory allocated on the GPU according to Ollama. "100% GPU" means where the model is loaded, not GPU load.',
      "Median and repeats: each run repeats the measurement (default 3) and shows the median with the min–max spread.",
    ],
    exactPrompt: "Exact prompt", promptLangNote: "The text stays in English in both languages.",
    copy: "Copy", copied: "Copied",
    credits: "Version & credits", creditsTech: "Tech stack",
    showPrompt: "Show prompt", hidePrompt: "Hide prompt",
    compareBtn: "Compare", compareOff: "Close comparison", selectModel: "Select model",
    genShort: "Speed", promptShort: "Prompt", firstShort: "1st token", totalShort: "Total", loadShort: "Load",
    winner: "Winner", tie: "Tie", ofMetrics: "metrics",
    clearHistory: "Clear history", clearHistoryConfirm: "Delete all results?",
    resetApp: "Reset app", resetAppConfirm: "Reset the app (history and preferences)?",
    yesClear: "Yes, delete", yesReset: "Yes, reset", cancel: "Cancel",
    cleared: "History cleared",
    shutdown: "Shut down", shutdownConfirm: "Stop Tokoflux?", yesShutdown: "Yes, stop",
    stopped: "Tokoflux stopped", stoppedHint: "You can close this tab.",
    contextLabel: "Context", gpuBudget: "GPU memory (GiB)",
    combinedSize: "Both models together: ≈ {n} GiB.",
    vramWarning: "Exceeds the GPU memory threshold ({n} GiB). Lower the context or run one model at a time to avoid ROCm errors.",
    rocmTitle: "GPU memory & ROCm errors",
    rocmList: [
      "Choose a smaller context (e.g. 2,048 or 4,096) to reduce the memory the model uses. The default is 8,192.",
      "The GPU memory threshold warns when two models together exceed the memory you want to leave to the GPU.",
      "To limit layers on the GPU, start Ollama with OLLAMA_NUM_GPU (e.g. 24) or cap VRAM with OLLAMA_MAX_VRAM (e.g. 16).",
      "Restart Ollama after changing these variables. On AMD iGPU (Strix Halo) the Vulkan backend may be more stable than ROCm.",
    ],
    claim: "handcrafted by a human, upgraded by agents",
  }
};
type Language = keyof typeof strings;
type Theme = "system" | "dark" | "light";
type Mode = "warm" | "cold";
type Run = {
  id: number; session: string | null; position: number | null;
  date: string; model: string; mode: Mode; first: number | null; total: number; load: number | null;
  prompt: number | null; decode: number | null; cached: number | null; gpu: number | null;
  context: number | null; tokens: number | null; stop: string | null;
};
type Status = { online: boolean; models: { name: string; size: number }[]; running: { name: string; size: number; size_vram?: number; context_length?: number }[] };
type Bench = { job: { status: "idle" | "running" | "complete" | "error"; model: string | null }; runs: Run[] };

type MetricKey = "decode" | "prompt" | "first" | "total" | "load" | "cached";

function median(values: (number | null | undefined)[]): number | null {
  const nums = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!nums.length) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function extent(values: (number | null | undefined)[]): [number, number] | null {
  const nums = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!nums.length) return null;
  return [Math.min(...nums), Math.max(...nums)];
}

type Summary = { model: string; count: number; date: string; stop: string | null } & Record<MetricKey, number | null>;

function summarize(group: Run[]): Summary {
  const last = group[group.length - 1];
  return {
    model: group[0]?.model ?? "",
    count: group.length,
    date: last?.date ?? "",
    stop: group.some(run => run.stop === "length") ? "length" : null,
    decode: median(group.map(run => run.decode)),
    prompt: median(group.map(run => run.prompt)),
    first: median(group.map(run => run.first)),
    total: median(group.map(run => run.total)),
    load: median(group.map(run => run.load)),
    cached: median(group.map(run => run.cached)),
  };
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, cache: "no-store" });
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}

function App() {
  const [lang, setLang] = useState<Language>(() => {
    const saved = localStorage.getItem("tokoflux.lang");
    return saved === "it" || saved === "en" ? saved : navigator.language.toLowerCase().startsWith("it") ? "it" : "en";
  });
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem("tokoflux.theme");
    return saved === "light" || saved === "dark" ? saved : "system";
  });
  const [status, setStatus] = useState<Status>();
  const [bench, setBench] = useState<Bench>({ job: { status: "idle", model: null }, runs: [] });
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("warm");
  const [starting, setStarting] = useState(false);
  const [readError, setReadError] = useState(false);
  const [launchError, setLaunchError] = useState(false);
  const [latestModel, setLatestModel] = useState("");
  const [compare, setCompare] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [copiedHelp, setCopiedHelp] = useState(false);
  const [context, setContext] = useState(DEFAULT_CONTEXT);
  const [vramBudget, setVramBudget] = useState<number>(() => {
    const saved = Number(localStorage.getItem("tokoflux.vramBudget"));
    return Number.isFinite(saved) && saved > 0 ? saved : 24;
  });
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [confirmShutdown, setConfirmShutdown] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [busyMaintain, setBusyMaintain] = useState(false);
  const t = strings[lang];
  const format = (n: number | null | undefined, digits = 1) =>
    n == null ? "—" : new Intl.NumberFormat(lang, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);
  const fmt = (s: string, n: number, digits = 1) => s.replace("{n}", format(n, digits));
  const date = (value: string) => new Intl.DateTimeFormat(lang, { dateStyle: "short", timeStyle: "short" }).format(new Date(value));

  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("tokoflux.lang", lang);
  }, [lang]);
  useEffect(() => {
    const preference = matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const current = theme === "system" ? (preference.matches ? "dark" : "light") : theme;
      document.documentElement.dataset.theme = current;
      document.querySelector('meta[name="theme-color"]')?.setAttribute("content", current === "dark" ? "#101616" : "#f4f3ec");
    };
    localStorage.setItem("tokoflux.theme", theme);
    preference.addEventListener("change", apply);
    apply();
    return () => preference.removeEventListener("change", apply);
  }, [theme]);
  useEffect(() => {
    api<{ prompt: string }>("/api/prompt").then(p => setPrompt(p.prompt)).catch(() => {});
  }, []);
  useEffect(() => {
    localStorage.setItem("tokoflux.vramBudget", String(vramBudget));
  }, [vramBudget]);
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      const [s, b] = await Promise.allSettled([api<Status>("/api/status"), api<Bench>("/api/benchmarks")]);
      if (!live) return;
      if (s.status === "fulfilled") setStatus(s.value);
      else setStatus(undefined);
      if (b.status === "fulfilled") setBench(b.value);
      setReadError(s.status === "rejected" || b.status === "rejected");
      timer = setTimeout(refresh, 2000);
    }
    void refresh();
    return () => { live = false; clearTimeout(timer); };
  }, []);

  const available = status?.models.map(m => m.name) ?? [];
  const sizeOf = (name: string) => status?.models.find(m => m.name === name)?.size ?? 0;
  const modelA = available.includes(first) ? first : available.includes("qwen3.8:27b") ? "qwen3.8:27b" : available[0] ?? "";
  const others = available.filter((name) => name !== modelA);
  const modelB = second === null ? (others.includes("inkling-2-mini:latest") ? "inkling-2-mini:latest" : "") : others.includes(second) ? second : "";
  const busy = starting || bench.job.status === "running";
  const sizeA = sizeOf(modelA);
  const sizeB = modelB ? sizeOf(modelB) : 0;
  const hasSizes = sizeA > 0 && (!modelB || sizeB > 0);
  const combinedGiB = hasSizes ? (sizeA + sizeB) / 2 ** 30 : 0;

  const runs = bench.runs;
  const firstSession = runs.find(run => run.session);
  const latestSession = firstSession
    ? runs.filter(run => run.session === firstSession.session).sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    : runs[0] ? [runs[0]] : [];
  const lastModels = [...new Set(latestSession.map(run => run.model))];
  const selectedLatest = lastModels.includes(latestModel) ? latestModel : lastModels[0] ?? "";
  const selectedGroup = latestSession.filter(run => run.model === selectedLatest);
  const summaryByModel = new Map(lastModels.map(model => [model, summarize(latestSession.filter(run => run.model === model))]));
  const selectedSummary = summaryByModel.get(selectedLatest) ?? summarize(selectedGroup);
  const spread = (key: MetricKey) => selectedSummary.count > 1 ? extent(selectedGroup.map(run => run[key])) : null;
  const decodeSpread = spread("decode");

  const chart = runs.filter(run => run.model === selectedLatest && run.decode !== null).slice(0, 12).reverse().map(run => ({
    speed: run.decode, label: date(run.date), model: run.model,
  }));

  async function start() {
    setStarting(true);
    setLaunchError(false);
    try {
      await api("/api/benchmarks", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: [modelA, modelB].filter(Boolean), mode, context }) });
      setBench(await api<Bench>("/api/benchmarks"));
    } catch { setLaunchError(true); }
    finally { setStarting(false); }
  }
  async function copy(text: string, setFlag: (value: boolean) => void) {
    try {
      await navigator.clipboard.writeText(text);
      setFlag(true);
      setTimeout(() => setFlag(false), 1500);
    } catch { /* clipboard unavailable */ }
  }
  async function clearHistory() {
    setBusyMaintain(true);
    try {
      await api("/api/history/clear", { method: "POST" });
      setBench(await api<Bench>("/api/benchmarks"));
    } catch { /* server unreachable */ }
    finally {
      setConfirmClear(false);
      setBusyMaintain(false);
    }
  }
  async function resetApp() {
    setBusyMaintain(true);
    try {
      await api("/api/history/clear", { method: "POST" });
    } catch { /* server unreachable */ }
    localStorage.removeItem("tokoflux.lang");
    localStorage.removeItem("tokoflux.theme");
    localStorage.removeItem("tokoflux.vramBudget");
    location.reload();
  }
  async function shutDown() {
    setConfirmShutdown(false);
    setStopped(true);
    try { await api("/api/shutdown", { method: "POST" }); } catch { /* already gone */ }
  }
  const compareModels = [modelA, modelB].filter(Boolean).map(model => {
    const group = latestSession.filter(run => run.model === model && run.mode === mode);
    const source = group.length ? group : (() => {
      const single = bench.runs.find(run => run.model === model && run.mode === mode);
      return single ? [single] : [];
    })();
    return { model, summary: summarize(source) };
  });
  const metrics = [
    { icon: Radio, label: t.prompt, value: selectedSummary.prompt, unit: t.units, spread: spread("prompt"), digits: 1 },
    { icon: Zap, label: t.first, value: selectedSummary.first, unit: "s", spread: spread("first"), digits: 2 },
    { icon: Timer, label: t.total, value: selectedSummary.total, unit: "s", spread: spread("total"), digits: 1 },
  ];
  const barMetrics: { key: "decode" | "prompt" | "first" | "total" | "load"; short: string; label: string; unit: string; lowerIsBetter: boolean; digits: number }[] = [
    { key: "decode", short: t.genShort, label: t.decode, unit: t.units, lowerIsBetter: false, digits: 1 },
    { key: "prompt", short: t.promptShort, label: t.prompt, unit: t.units, lowerIsBetter: false, digits: 1 },
    { key: "first", short: t.firstShort, label: t.first, unit: "s", lowerIsBetter: true, digits: 2 },
    { key: "total", short: t.totalShort, label: t.total, unit: "s", lowerIsBetter: true, digits: 1 },
    { key: "load", short: t.loadShort, label: t.load, unit: "s", lowerIsBetter: true, digits: 3 },
  ];
  const score = (value: number | null, other: number | null, lowerIsBetter: boolean) => {
    if (typeof value !== "number" || typeof other !== "number") return 0;
    const best = lowerIsBetter ? Math.min(value, other) : Math.max(value, other);
    if (best <= 0) return 0;
    return Math.round((lowerIsBetter ? best / value : value / best) * 100);
  };
  const compareBars = barMetrics.map(m => {
    const a = summaryByModel.get(lastModels[0])?.[m.key] ?? null;
    const b = summaryByModel.get(lastModels[1])?.[m.key] ?? null;
    const row: Record<string, unknown> = { label: m.short, fullLabel: m.label, unit: m.unit, digits: m.digits, lowerIsBetter: m.lowerIsBetter };
    row.values = { [lastModels[0]]: a, [lastModels[1]]: b };
    row[lastModels[0]] = score(a, b, m.lowerIsBetter);
    row[lastModels[1]] = score(b, a, m.lowerIsBetter);
    return row;
  });
  const winnerInfo = (() => {
    const wins: Record<string, number> = {};
    lastModels.forEach(m => wins[m] = 0);
    let counted = 0;
    barMetrics.forEach(m => {
      const a = summaryByModel.get(lastModels[0])?.[m.key] ?? null;
      const b = summaryByModel.get(lastModels[1])?.[m.key] ?? null;
      if (typeof a !== "number" || typeof b !== "number" || a === b) return;
      counted++;
      const best = m.lowerIsBetter ? Math.min(a, b) : Math.max(a, b);
      wins[a === best ? lastModels[0] : lastModels[1]]++;
    });
    const sorted = [...lastModels].sort((x, y) => wins[y] - wins[x]);
    const winner = lastModels.length > 1 && wins[sorted[0]] > wins[sorted[1]] ? sorted[0] : null;
    return { winner, winCount: winner ? wins[winner] : 0, metricCount: counted };
  })();

  return <>
    <header className="top"><div className="wrap toprow">
      <a className="brand" href="/" aria-label="Tokoflux"><img src="/icon.svg" alt="" /><span>Tokoflux<small>{t.sub}</small></span></a>
      <div className="toolbar">
        <button type="button" className="switch help-btn" onClick={() => setHelpOpen(true)}><HelpCircle size={16} />{t.help}</button>
        <label className="switch"><Languages size={16} /><span className="sr-only">{t.lang}</span>
          <select value={lang} onChange={(e) => setLang(e.target.value as Language)}><option value="it">IT</option><option value="en">EN</option></select>
        </label>
        <label className="switch"><Monitor size={16} /><span className="sr-only">{t.theme}</span>
          <select value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
            <option value="system">{t.system}</option><option value="light">{t.light}</option><option value="dark">{t.dark}</option>
          </select>
        </label>
        <button type="button" className="switch help-btn shutdown-btn" onClick={() => setConfirmShutdown(true)}><Power size={16} />{t.shutdown}</button>
      </div>
    </div></header>
    <main className="wrap">
      <div className="intro">
        <div><h1>{t.title}<span>.</span></h1><p>{t.desc}</p></div>
        <div className="status" data-online={status?.online ?? false}><i />{readError ? t.failed : status ? status.online ? t.online : t.offline : t.connecting}</div>
      </div>
      <div className="overview">
        <section className="panel hero">
          <div className="hero-head">
            <span className="eyebrow"><Activity size={17} />{t.latest}</span>
            <div className="hero-controls">
              {lastModels.length > 1 && <label className="switch"><span className="sr-only">{t.selectModel}</span>
                <select value={selectedLatest} onChange={(e) => setLatestModel(e.target.value)}>{lastModels.map(m => <option key={m} value={m}>{m}</option>)}</select>
              </label>}
              {lastModels.length > 1 && <Button type="button" variant={compare ? "primary" : "outline"} onClick={() => setCompare(v => !v)}>
                {compare ? <X size={15} /> : <ArrowRightLeft size={15} />}{compare ? t.compareOff : t.compareBtn}</Button>}
              {lastModels.length <= 1 && selectedSummary.model && <span className="chip">{selectedSummary.model}</span>}
            </div>
          </div>
          {compare && lastModels.length > 1 ? <>
            <div className="vs-head">
              <span className="vs-item"><i style={{ background: COLORS[0] }} />{lastModels[0]}</span>
              <span className="vs-sep">vs</span>
              <span className="vs-item"><i style={{ background: COLORS[1] }} />{lastModels[1]}</span>
            </div>
            <div className="plot compare-plot" role="img" aria-label={t.comparison}>
              <ResponsiveContainer width="100%" height="100%"><BarChart data={compareBars} margin={{ top: 14, right: 8, left: -16, bottom: 0 }} barCategoryGap="26%" barGap={4}>
                <defs>
                  <linearGradient id="barA" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--plot)" /><stop offset="100%" stopColor="var(--plot)" stopOpacity={0.45} /></linearGradient>
                  <linearGradient id="barB" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--cyan)" /><stop offset="100%" stopColor="var(--cyan)" stopOpacity={0.45} /></linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="4 6" />
                <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} interval={0} />
                <YAxis domain={[0, 100]} hide />
                <Tooltip cursor={{ fill: "var(--surface-raised)", opacity: 0.6 }} contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10 }}
                  labelFormatter={(label, payload) => payload?.[0]?.payload?.fullLabel ?? label}
                  formatter={(value, name, item) => {
                    const row = item?.payload as { values?: Record<string, number | null>; unit?: string; digits?: number } | undefined;
                    const actual = row?.values?.[String(name)] ?? null;
                    const unit = row?.unit ? " " + row.unit : "";
                    return [actual == null ? "—" : format(actual, row?.digits ?? 1) + unit + " · " + Math.round(Number(value)) + "%", String(name)];
                  }} />
                <Bar dataKey={lastModels[0]} name={lastModels[0]} fill="url(#barA)" radius={[6, 6, 0, 0]} maxBarSize={40} isAnimationActive animationDuration={700} />
                <Bar dataKey={lastModels[1]} name={lastModels[1]} fill="url(#barB)" radius={[6, 6, 0, 0]} maxBarSize={40} isAnimationActive animationDuration={700} />
              </BarChart></ResponsiveContainer>
            </div>
            <div className="winner"><Trophy size={15} />
              {winnerInfo.winner ? <span>{t.winner} <strong>{winnerInfo.winner}</strong> · {winnerInfo.winCount}/{winnerInfo.metricCount} {t.ofMetrics}</span> : <span>{t.tie}</span>}
            </div>
          </> : <>
            <div className="lead"><div>{t.decode}</div><strong>{format(selectedSummary.decode)}</strong><span>{t.units}</span>
              {decodeSpread && <em className="spread" title={t.spread}>{format(decodeSpread[0])}–{format(decodeSpread[1])} {t.units}</em>}
            </div>
            {chart.length > 1 ? <div className="plot" role="img" aria-label={t.trend}>
              <ResponsiveContainer width="100%" height="100%"><AreaChart data={chart} margin={{ top: 8, right: 4, left: 4, bottom: 1 }}>
                <defs><linearGradient id="signal" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--plot)" stopOpacity={0.37} /><stop offset="100%" stopColor="var(--plot)" stopOpacity={0.02} /></linearGradient></defs>
                <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="4 6" />
                <XAxis dataKey="label" hide /><YAxis domain={[0, "auto"]} hide />
                <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10 }}
                  labelFormatter={(label, payload) => payload?.[0]?.payload?.model + " · " + label}
                  formatter={(v) => [format(typeof v === "number" ? v : null) + " " + t.units, t.decode]} />
                <Area type="linear" dataKey="speed" stroke="var(--plot)" strokeWidth={2} fill="url(#signal)" isAnimationActive={false} />
              </AreaChart></ResponsiveContainer>
            </div> : <div className="plot-empty"><ChartNoAxesCombined size={17} />{selectedSummary.count > 0 ? t.trend : t.empty}</div>}
            <div className="metric-grid">{metrics.map(({ icon: Icon, label, value, unit, spread: range, digits }) =>
              <div className="metric" key={label}><span><Icon size={15} />{label}</span><strong>{format(value)}</strong> <small>{unit}</small>
                {range && <em className="spread" title={t.spread}>{format(range[0], digits)}–{format(range[1], digits)} {unit}</em>}
              </div>
            )}</div>
          </>}
        </section>
        <section className="panel resources">
          <h2><Cpu size={21} />{t.hardware}</h2>
          {status?.running.length ? status.running.map(m => {
            const gpu = m.size && m.size_vram != null ? Math.round(100 * m.size_vram / m.size) : null;
            return <div className="active" key={m.name}>
              <div className="active-top"><strong>{m.name}</strong><span>{format(gpu, 0)}{gpu !== null && "%"}</span></div>
              <div className="bar" aria-hidden="true"><div style={{ width: (gpu ?? 0) + "%" }} /></div>
              <p>{t.gpu}</p>
              <dl><div><dt>{t.context}</dt><dd>{format(m.context_length, 0)} {t.tokens}</dd></div>
                <div><dt>{t.memory}</dt><dd>{format(m.size / 2 ** 30)} GiB</dd></div></dl>
              <small>{t.usage}</small>
            </div>;
          }) : <div className="resource-empty"><Gauge size={44} strokeWidth={1} /><p>{t.noActive}</p></div>}
        </section>
      </div>
      <section className="panel bench">
        <div className="section-head"><div><h2><FlaskConical size={21} />{t.benchmark}</h2><p>{t.benchmarkDesc}</p></div>
          <Button type="button" disabled={busy || !status?.online || !modelA} onClick={start}>{busy ? <Activity size={17} className="pulse" /> : <Play size={16} fill="currentColor" />}{busy ? t.running : t.start}</Button></div>
        <div className="fields">
          <label>{t.modelA}<select value={modelA} disabled={busy || !available.length} onChange={e => setFirst(e.target.value)}>
            {!available.length && <option value="">{t.noModels}</option>}{available.map(m => <option key={m}>{m}</option>)}
          </select></label>
          <label>{t.modelB}<select value={modelB} disabled={busy || !others.length} onChange={e => setSecond(e.target.value)}>
            <option value="">{t.none}</option>{others.map(m => <option key={m}>{m}</option>)}
          </select></label>
          <label>{t.mode}<select value={mode} disabled={busy} onChange={e => setMode(e.target.value as Mode)}>
            <option value="warm">{t.warm}</option><option value="cold">{t.cold}</option>
          </select></label>
          <label>{t.contextLabel}<select value={context} disabled={busy} onChange={e => setContext(Number(e.target.value))}>
            {CONTEXT_OPTIONS.map(c => <option key={c} value={c}>{format(c, 0)}</option>)}
          </select></label>
        </div>
        {modelB && hasSizes && <div className="vram">
          <label className="vram-budget"><span>{t.gpuBudget}</span>
            <input type="number" min={1} max={512} step={1} value={vramBudget} disabled={busy}
              onChange={e => setVramBudget(Math.min(512, Math.max(1, Number(e.target.value) || 1)))} />
          </label>
          <p className={combinedGiB > vramBudget ? "warn" : ""}>
            {combinedGiB > vramBudget ? fmt(t.vramWarning, vramBudget, 0) : fmt(t.combinedSize, combinedGiB, 1)}
          </p>
        </div>}
        <p className="hint">{mode === "warm" ? t.warmHelp : t.coldHelp}</p>
        <div className="prompt">
          <button type="button" className="prompt-toggle" onClick={() => setPromptOpen(v => !v)} aria-expanded={promptOpen}>
            <Code2 size={15} />{promptOpen ? t.hidePrompt : t.showPrompt}<ChevronDown size={15} className={promptOpen ? "open" : ""} />
          </button>
          {promptOpen && <div className="prompt-body">
            <p className="prompt-note">{t.promptLangNote}</p>
            <pre>{prompt || "…"}</pre>
            <Button type="button" variant="outline" disabled={!prompt} onClick={() => copy(prompt, setCopiedPrompt)}>
              {copiedPrompt ? <Check size={15} /> : <Copy size={15} />}{copiedPrompt ? t.copied : t.copy}</Button>
          </div>}
        </div>
        <div className="feedback" aria-live="polite">
          {busy ? <span>{t.running}{bench.job.model && " · " + bench.job.model}</span> :
            launchError || bench.job.status === "error" ? <span className="error">{t.error}</span> :
            bench.job.status === "complete" ? <span>{t.done}</span> : null}
        </div>
        {compareModels.length > 0 && <div className="comparison">
          <h3>{t.comparison} <span>· {t[mode]}</span></h3>
          <div className="compare-grid">{compareModels.map(({ model, summary }) => <article key={model}>
            <div><strong>{model}</strong><small>{summary.count ? date(summary.date) : "—"}{summary.count > 1 && " · " + fmt(t.repeats, summary.count)}</small></div>
            <dl>{[
              [t.decode, summary.decode, t.units], [t.prompt, summary.prompt, t.units], [t.first, summary.first, "s"],
              [t.total, summary.total, "s"], [t.load, summary.load, "s"], [t.cached, summary.cached, ""],
            ].map(([label, value, unit]) => <div key={String(label)}><dt>{label}</dt><dd>{format(value as number | null, label === t.cached ? 0 : 1)} {unit}</dd></div>)}</dl>
            {summary.stop === "length" && <small className="error">{t.limit}</small>}
          </article>)}</div>
        </div>}
      </section>
      <section className="panel history">
        <div className="history-head">
          <h2><History size={21} />{t.history}</h2>
          <div className="history-actions">
            {bench.runs.length > 0 && (confirmClear ? <div className="maintain">
              <span>{t.clearHistoryConfirm}</span>
              <Button type="button" variant="primary" disabled={busyMaintain} onClick={clearHistory}>{t.yesClear}</Button>
              <Button type="button" variant="outline" disabled={busyMaintain} onClick={() => setConfirmClear(false)}>{t.cancel}</Button>
            </div> : <Button type="button" variant="outline" onClick={() => { setConfirmClear(true); setConfirmReset(false); }}><Trash2 size={15} />{t.clearHistory}</Button>)}
            {confirmReset ? <div className="maintain">
              <span>{t.resetAppConfirm}</span>
              <Button type="button" variant="primary" disabled={busyMaintain} onClick={resetApp}>{t.yesReset}</Button>
              <Button type="button" variant="outline" disabled={busyMaintain} onClick={() => setConfirmReset(false)}>{t.cancel}</Button>
            </div> : <Button type="button" variant="outline" onClick={() => { setConfirmReset(true); setConfirmClear(false); }}><RotateCcw size={15} />{t.resetApp}</Button>}
          </div>
        </div>
        {bench.runs.length ? <div className="scroll"><table>
          <thead><tr>{[t.date, t.model, t.mode, t.prompt, t.decode, t.first, t.total].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>{bench.runs.map((r, i) => <tr key={r.id ?? r.date + i}><td>{date(r.date)}</td><td>{r.model}</td><td>{t[r.mode]}</td>
            <td>{format(r.prompt)} {t.units}</td><td>{format(r.decode)} {t.units}</td><td>{format(r.first)} s</td><td>{format(r.total)} s</td></tr>)}</tbody>
        </table></div> : <p>{t.empty}</p>}
      </section>
    </main>
    <footer className="footer"><div className="wrap footer-row">
      <span className="footer-brand">Tokoflux v{VERSION}</span>
      <span className="footer-meta"><a href={AUTHOR_URL} target="_blank" rel="noreferrer">Rosario Moscato</a><span aria-hidden="true">·</span><span>{t.claim}</span></span>
    </div></footer>
    <div className="drawer-backdrop" data-open={helpOpen} onClick={() => setHelpOpen(false)} />
    <aside className="drawer" data-open={helpOpen} role="dialog" aria-modal="false" aria-label={t.helpTitle} inert={!helpOpen}>
      <div className="drawer-head">
        <h2><HelpCircle size={20} />{t.helpTitle}</h2>
        <button type="button" onClick={() => setHelpOpen(false)}><X size={18} /><span className="sr-only">{t.close}</span></button>
      </div>
      <div className="drawer-body">
        <section><h3>{t.howToStart}</h3><p>{t.howToStartText}</p></section>
        <section><h3>{t.warmCold}</h3><p>{t.warmColdText}</p></section>
        <section><h3>{t.whatPrompt}</h3><p>{t.whatPromptText}</p><p className="note">{t.testsNote}</p></section>
        <section><h3>{t.readMetrics}</h3><ul>{t.readMetricsList.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section><h3>{t.rocmTitle}</h3><ul>{t.rocmList.map(item => <li key={item}>{item}</li>)}</ul></section>
        <section><h3>{t.exactPrompt}</h3><p className="prompt-note">{t.promptLangNote}</p><pre>{prompt || "…"}</pre>
          <Button type="button" variant="outline" disabled={!prompt} onClick={() => copy(prompt, setCopiedHelp)}>
            {copiedHelp ? <Check size={15} /> : <Copy size={15} />}{copiedHelp ? t.copied : t.copy}</Button>
        </section>
        <section><h3>{t.credits}</h3>
          <p className="credits-line">Tokoflux v{VERSION}</p>
          <p className="credits-line"><a href={AUTHOR_URL} target="_blank" rel="noreferrer">Rosario Moscato</a></p>
          <p className="credits-tech"><span>{t.creditsTech}:</span> Python 3.12 · SQLite · React · TypeScript · Vite · Tailwind · shadcn/ui · Recharts</p>
        </section>
      </div>
    </aside>
    {confirmShutdown && <div className="modal-backdrop" onClick={() => setConfirmShutdown(false)}>
      <div className="modal" role="dialog" aria-modal="true" onClick={e => e.stopPropagation()}>
        <div className="modal-icon"><Power size={22} /></div>
        <h2>{t.shutdown}</h2>
        <p>{t.shutdownConfirm}</p>
        <div className="modal-actions">
          <Button type="button" variant="outline" onClick={() => setConfirmShutdown(false)}>{t.cancel}</Button>
          <Button type="button" variant="primary" onClick={shutDown}>{t.yesShutdown}</Button>
        </div>
      </div>
    </div>}
    {stopped && <div className="stopped" role="dialog" aria-modal="true">
      <div className="stopped-card">
        <div className="stopped-icon"><Power size={30} /></div>
        <h2>{t.stopped}</h2>
        <p>{t.stoppedHint}</p>
      </div>
    </div>}
  </>;
}

createRoot(document.getElementById("root")!).render(<App />);
