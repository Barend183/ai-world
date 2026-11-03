"""Grows Sprout's own brain a little, from his own lessons. Runs on Kaggle's free GPU (started by grow.yml).

Input:  /kaggle/input/sprout-lessons/lessons.jsonl  (chat examples: what he took in -> what he decided)
Output: /kaggle/working/sprout.gguf + Modelfile + meta.json  (his brain, ready for Ollama, and its test results)

A small open model (Qwen3 1.7B, Apache-2.0) learns from the lessons with LoRA (a light layer of new learning
on top), is tested on lessons it never saw, then merged and packed into one file Ollama can run on a CPU.
"""
import glob
import json
import os
import random
import re
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "peft>=0.13", "gguf", "sentencepiece", "protobuf"], check=True)

import torch  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

BASE = os.environ.get("SPROUT_BASE", "Qwen/Qwen3-1.7B")
OUT = "/kaggle/working"
MAX_LEN = 3072
random.seed(7)

src = glob.glob("/kaggle/input/**/lessons.jsonl", recursive=True)[0]
examples = [json.loads(line) for line in open(src, encoding="utf-8") if line.strip()]
random.shuffle(examples)
held = examples[: max(20, len(examples) // 20)]
train = examples[len(held):]
print(f"{len(train)} lessons to learn from, {len(held)} kept aside for the test")

tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16, device_map="cuda")
model.gradient_checkpointing_enable()
model.enable_input_require_grads()
model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                         target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))


def prompt_of(msgs):
    return tok.apply_chat_template(msgs[:2], tokenize=False, add_generation_prompt=True, enable_thinking=False)


def encode(ex):
    """Learn only the answer: the prompt tokens are there for context but don't count towards the loss."""
    p = tok(prompt_of(ex["messages"]), add_special_tokens=False)["input_ids"]
    a = tok(ex["messages"][2]["content"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
    p = p[-(MAX_LEN - len(a)):] if len(p) + len(a) > MAX_LEN else p
    return p + a, [-100] * len(p) + a


data = [encode(e) for e in train]
epochs = 2 if len(data) < 800 else 1
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1.5e-4)
scaler = torch.amp.GradScaler("cuda")
accum, step = 8, 0
model.train()
for epoch in range(epochs):
    random.shuffle(data)
    for i, (ids, labels) in enumerate(data):
        x = torch.tensor([ids], device="cuda")
        y = torch.tensor([labels], device="cuda")
        with torch.autocast("cuda", dtype=torch.float16):
            loss = model(input_ids=x, labels=y).loss / accum
        scaler.scale(loss).backward()
        if (i + 1) % accum == 0 or i + 1 == len(data):
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            opt.zero_grad()
            step += 1
            if step % 20 == 0:
                print(f"epoch {epoch + 1}, step {step}, loss {loss.item() * accum:.3f}", flush=True)

# The test: on lessons it never saw, does it answer with a usable thought (valid JSON, a real action)?
model.eval()
actions = set(re.findall(r"[a-z_]+", held[0]["messages"][0]["content"].split("My actions:")[-1]))
valid = same = 0
for ex in held:
    ids = tok(prompt_of(ex["messages"]), return_tensors="pt", add_special_tokens=False).input_ids[:, -MAX_LEN:].to("cuda")
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        out = model.generate(ids, max_new_tokens=400, do_sample=False, pad_token_id=tok.eos_token_id)
    text = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
    try:
        reply = json.loads(text[text.index("{"): text.rindex("}") + 1])
        if reply.get("action") in actions and isinstance(reply.get("thought"), str):
            valid += 1
            same += reply["action"] == json.loads(ex["messages"][2]["content"]).get("action")
    except (ValueError, AttributeError):
        pass
meta = {"base": BASE, "lessons": len(train), "tested": len(held), "valid": round(valid / len(held), 3),
        "same_choice": round(same / len(held), 3), "epochs": epochs}
print("test:", meta)

# Pack it: merge the new learning into the model, then one GGUF file for Ollama.
merged = model.merge_and_unload()
merged.save_pretrained(f"{OUT}/merged", safe_serialization=True)
tok.save_pretrained(f"{OUT}/merged")
subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/ggml-org/llama.cpp", "/tmp/llama.cpp"], check=True)
subprocess.run([sys.executable, "/tmp/llama.cpp/convert_hf_to_gguf.py", f"{OUT}/merged", "--outtype", "q8_0",
                "--outfile", f"{OUT}/sprout.gguf"], check=True)
subprocess.run(["rm", "-rf", f"{OUT}/merged"], check=True)
with open(f"{OUT}/Modelfile", "w") as f:
    f.write('FROM ./sprout.gguf\n'
            'TEMPLATE """{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n{{ end }}'
            '{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}'
            '<|im_start|>assistant\n<think>\n\n</think>\n\n{{ .Response }}<|im_end|>\n"""\n'
            'PARAMETER stop "<|im_end|>"\nPARAMETER temperature 0.7\n')
with open(f"{OUT}/meta.json", "w") as f:
    json.dump(meta, f)
print("done")
