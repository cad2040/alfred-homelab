# Ollama Modelfiles (template defaults)

Bootstrap pulls base weights, then `ollama create`s these tags so LiteLLM aliases
match the reference 12GB-class map (`MAX_LOADED=1`).

| Local tag | Base pull | Why a Modelfile |
|-----------|-----------|-----------------|
| `alfred-coder-14b` | `qwen2.5-coder:14b-instruct-q3_K_M` | Force `num_ctx=16384` (OpenAI `/v1` ignores `options.num_ctx`) |
| `alfred-reasoner` | `qwen3.5:9b` | 32k ctx + reasoner SYSTEM |
| `alfred-planner` | `qwen3.5:9b` | 32k ctx + Spec Kit planner SYSTEM |
| `alfred-foundation-sec` | `hf.co/mradermacher/Foundation-Sec-8B-Instruct-GGUF:Q4_K_M` | Instruct chat template (not base) |

FIM (`qwen2.5-coder:1.5b-base`) needs no Modelfile — optional Bronze fallback.
