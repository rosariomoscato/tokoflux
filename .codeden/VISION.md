# Vision

Tokoflux is a local, privacy-first benchmark and monitor for Ollama models on Windows. It measures how AI models respond on the user's own hardware — speed (time to first token, tokens/s, total time) and resource usage (GPU/VRAM share, context) — and lets users compare models head-to-head, with results stored locally. It ships as a self-contained launcher (a standard-library Python server plus a prebuilt React frontend) that needs no Node.js or npm at runtime.

## Goals
- Give Windows users a one-click, zero-dependency way to benchmark and compare local Ollama models on their own hardware.
- Make measurements trustworthy: repeated runs with median/spread instead of a single noisy sample.
- Add a quality axis: execute the generated code (and its unit tests) in a sandbox so users choose models on speed and correctness together.
- Let users benchmark their own workloads (custom prompts / prompt suites), not only the built-in coding prompt.
- Stay local and private: store metrics only, never generated text; serve only on 127.0.0.1.
- Keep the runtime dependency-free (Python stdlib backend, prebuilt frontend) and the install/uninstall one-click.

## Target users
- Local-LLM enthusiasts and developers running Ollama on Windows, often on AMD GPUs / iGPUs (ROCm or Vulkan).
- People deciding which local model to keep or use for a task: they need repeatable speed numbers, a correctness signal, and clear guidance on GPU memory and ROCm pitfalls.
- Non-expert users who want a simple launcher, a bilingual UI (IT/EN), and easy management of their history.

## Principles
- Small, well-tested changes
- Keep the public API stable (the frontend/backend HTTP contract under `/api/*`)
- Standard-library-only backend; never add a runtime dependency for the user
- Privacy first: store metrics only, never generated text; listen only on 127.0.0.1

## Out of scope
- Cloud or remote model hosting, accounts, or SaaS features
- Multi-user, networked, or multi-machine deployments beyond the local PC
- Model runtimes other than Ollama
- Storing or transmitting generated output text

## Quality bar
- Every behaviour change comes with tests (backend logic: validation, benchmark, save/history)
- CI is green before merge (`npm run build` and backend tests pass)

## Protected areas
Paths (globs in backticks) and topics that always need a human. The factory never merges
changes that touch them; they go to your inbox.
- `**/auth/**`
- `**/migrations/**`
- `.github/workflows/**`
- `LICENSE`
- `Installa-Tokoflux.cmd`
- `Disinstalla-Tokoflux.cmd`
- `Disinstalla-Tokoflux.ps1`
- payments
- licensing
