# GB10 runbook: do these in order, and stop at the first failure

Nothing here has been run on a GB10 by Claude. Every step has a check. If a check fails, use the fallback; don't debug for more than 15 minutes.

## 0. Arrive, check in (09:00)
- Confirm the build start time, the submission dashboard, and the required stack (NemoClaw / OpenClaw / OpenShell).
- Confirm which messaging channel counts: Slack, Discord or Telegram.
- Optional: ask whether prepared libraries are OK (the rule as we recorded it says yes).

## 1. Copy the kit and test it (5 min)
```bash
lsblk; ls /media/$USER/                 # the SSD 'GBeast10' should auto-mount (exFAT)
A=/media/$USER/GBeast10/GB10_ARSENAL
mkdir -p ~/gmaps && cp -r $A/gmaps/gmaps_prep_kit/. ~/gmaps/ && cd ~/gmaps
git init; git add -A; git -c user.name="Franco" -c user.email="franco@local" commit -m "import prepared libraries (built Oct 2-3 before the event)"
python3 tests/run_all.py                # expect 53/53
```
If `jsonschema` is missing, the graph check FAILS on purpose. DGX OS (Ubuntu 24.04) blocks system-wide pip with an "externally-managed-environment" error, so use a venv: `python3 -m venv ~/gvenv && ~/gvenv/bin/pip install jsonschema && ~/gvenv/bin/python tests/run_all.py`. Or use `pip install --user --break-system-packages jsonschema`.

## 2. vLLM container + Nemotron 3 Nano NVFP4 (20–40 min, most of it downloading)
The model card names container `nvcr.io/nvidia/vllm:25.12.post1-py3` for DGX Spark.
```bash
docker pull nvcr.io/nvidia/vllm:25.12.post1-py3      # on venue network; several GB
docker run --gpus all -it --rm --name gmaps-vllm --ipc=host -p 8000:8000 \
  -v $A/models:/models -v ~/gmaps:/gmaps -v $A/wheels:/wheels \
  nvcr.io/nvidia/vllm:25.12.post1-py3 bash
# inside the container:
cd /models/reasoning/nemotron-3-nano-30b-a3b-nvfp4
VLLM_USE_FLASHINFER_MOE_FP4=1 VLLM_FLASHINFER_MOE_BACKEND=throughput \
vllm serve /models/reasoning/nemotron-3-nano-30b-a3b-nvfp4 \
  --served-model-name model --max-num-seqs 4 --tensor-parallel-size 1 \
  --max-model-len 32768 --gpu-memory-utilization 0.55 --port 8000 \
  --trust-remote-code --enable-auto-tool-choice --tool-call-parser qwen3_coder \
  --reasoning-parser-plugin nano_v3_reasoning_parser.py --reasoning-parser nano_v3 \
  --kv-cache-dtype fp8
```
What I changed from the model card, and why:
- I set `--max-model-len 32768` instead of 262144, because we only need short prompts and it leaves memory for Whisper.
- I added `--gpu-memory-utilization 0.55` to keep headroom for Whisper.
- If either flag is rejected, follow the README.md in that model folder (it's on the SSD).

**Check** (from a second terminal):
```bash
curl -s localhost:8000/v1/models | head
curl -s localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"model","messages":[{"role":"user","content":"Reply with the word ready."}],"chat_template_kwargs":{"enable_thinking":false},"max_tokens":5}'
```
Then test the residue parser:
```bash
cd ~/gmaps && python3 -c "import sys;sys.path.insert(0,'lib');from gmaps_core.adapters import LocalLLM;print(LocalLLM().parse_residue('2384 we had an anti-ice light come on','KLGA'))"
```
**If it fails:**
- Try Qwen3-4B-Instruct-2507: `vllm serve /models/reasoning/qwen3-4b-instruct --served-model-name model --max-model-len 16384 --gpu-memory-utilization 0.3 --enable-auto-tool-choice --tool-call-parser hermes`.
- The grammar parser works with no model at all, so the demo never depends on the language model for the critical fields.
- Write down the exact error for the write-up.

## 3. Whisper large-v3-turbo (10 min)
Run it in the same container (it already has torch with CUDA and transformers). `vllm serve` is holding the first shell, so open a second one into it:
```bash
docker exec -it gmaps-vllm bash
pip install --no-index --find-links /wheels soundfile librosa || pip install soundfile librosa
cd /gmaps && python3 -c "
import sys; sys.path.insert(0,'lib')
from gmaps_core.adapters import transcribe
print(transcribe('/gmaps/audio/SIM_E1_CROSS_DURING_ROLLOUT_28.wav', '/models/speech/whisper-large-v3-turbo'))"
```
You need a clip first: record one line from `docs/REVOICE_SCRIPT.md`, or generate one with Kokoro.

**Check:** the text contains "cross runway 36 at Kilo" or similar. Then confirm the parser types it:
```bash
python3 -c "import sys;sys.path.insert(0,'lib');from gmaps_core.parser import parse;from gmaps_core.sim.simmap import SimAirport;print(parse('<paste ASR text>','XSIM',resolver=SimAirport()))"
```
**If it fails:** Parakeet (`/models/speech/parakeet-tdt-0.6b-v2`) needs NeMo, which is not in the vLLM container, so don't chase it. Instead, use pre-segmented clips with the reference transcript and label the demo "ASR not running". Never present a transcript as live ASR when it isn't.

## 4. Agent assembly (the real build): see `AGENT_ASSEMBLY_PLAN.md`

## 5. Display
```bash
cd ~/gmaps/ui_scaffold && python3 -m http.server 8765    # open http://localhost:8765
```
To show a run produced by the live agent, write its timeline to `ui_scaffold/samples/live.json` and open `?f=samples/live.json`.

## Memory budget (plan, not measured)
- Nemotron NVFP4 at about 0.55 of unified memory
- Whisper turbo fp16, about 2 GB
- Everything else is small

**Do not** load the healthcare, coding, vision or speech-generation models while serving.

## Fallback ladder (decide fast, label honestly)
1. **Everything works:** live re-voiced clip → ASR → parser/LLM tools → ledger + look-ahead → display → channel post.
2. **ASR broken:** pre-segmented clips with reference transcripts. Say so on screen.
3. **LLM broken:** grammar parser only. The tool loop is missing, so tell a mentor what's missing; never fake a trace.
4. **Mandatory stack or channel broken:** consult a mentor and report the exact missing component.
