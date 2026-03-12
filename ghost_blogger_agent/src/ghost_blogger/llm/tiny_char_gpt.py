from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ghost_blogger.net import redact_pii_like

from . import LLM


@dataclass(frozen=True)
class TinyCharGPTLLM(LLM):
    model: object
    encode: object
    decode: object
    temperature: float
    max_new_chars: int
    device: str

    @classmethod
    def try_create(
        cls,
        *,
        checkpoint_path: Path,
        vocab_text_path: Path,
        temperature: float,
        max_new_chars: int,
    ) -> Optional["TinyCharGPTLLM"]:
        try:
            import torch
            import torch.nn as nn
            from torch.nn import functional as F
        except Exception:
            return None

        text = vocab_text_path.read_text(encoding="utf-8", errors="ignore")
        chars = sorted(set(text))
        if not chars:
            return None
        stoi = {c: i for i, c in enumerate(chars)}
        itos = {i: c for i, c in enumerate(chars)}

        def encode(s: str) -> list[int]:
            # replace out-of-vocab characters with space
            return [stoi.get(c, stoi.get(" ", 0)) for c in s]

        def decode(toks: list[int]) -> str:
            return "".join(itos.get(i, "") for i in toks)

        # These hyperparams must match the training script that produced the checkpoint.
        BLOCK_SIZE = 128
        N_EMBD = 64
        N_HEAD = 4
        N_LAYER = 4
        DROPOUT = 0.1

        vocab_size = len(chars)
        device = "cuda" if torch.cuda.is_available() else "cpu"

        class CausalSelfAttention(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                assert N_EMBD % N_HEAD == 0
                self.c_attn = nn.Linear(N_EMBD, 3 * N_EMBD)
                self.c_proj = nn.Linear(N_EMBD, N_EMBD)
                self.attn_drop = nn.Dropout(DROPOUT)
                self.resid_drop = nn.Dropout(DROPOUT)
                self.n_head = N_HEAD
                self.head_dim = N_EMBD // N_HEAD
                self.register_buffer(
                    "bias",
                    torch.tril(torch.ones(BLOCK_SIZE, BLOCK_SIZE)).view(1, 1, BLOCK_SIZE, BLOCK_SIZE),
                )

            def forward(self, x):  # type: ignore[no-untyped-def]
                B, T, C = x.shape
                q, k, v = self.c_attn(x).split(N_EMBD, dim=2)
                q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
                k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
                v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

                att = (q @ k.transpose(-2, -1)) * (self.head_dim**-0.5)
                att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
                att = F.softmax(att, dim=-1)
                att = self.attn_drop(att)
                y = att @ v
                y = y.transpose(1, 2).contiguous().view(B, T, C)
                return self.resid_drop(self.c_proj(y))

        class MLP(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(N_EMBD, 4 * N_EMBD),
                    nn.GELU(),
                    nn.Linear(4 * N_EMBD, N_EMBD),
                    nn.Dropout(DROPOUT),
                )

            def forward(self, x):  # type: ignore[no-untyped-def]
                return self.net(x)

        class Block(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.ln1 = nn.LayerNorm(N_EMBD)
                self.attn = CausalSelfAttention()
                self.ln2 = nn.LayerNorm(N_EMBD)
                self.mlp = MLP()

            def forward(self, x):  # type: ignore[no-untyped-def]
                x = x + self.attn(self.ln1(x))
                x = x + self.mlp(self.ln2(x))
                return x

        class GPT(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.tok_emb = nn.Embedding(vocab_size, N_EMBD)
                self.pos_emb = nn.Embedding(BLOCK_SIZE, N_EMBD)
                self.drop = nn.Dropout(DROPOUT)
                self.blocks = nn.Sequential(*[Block() for _ in range(N_LAYER)])
                self.ln_f = nn.LayerNorm(N_EMBD)
                self.head = nn.Linear(N_EMBD, vocab_size, bias=False)

            def forward(self, idx):  # type: ignore[no-untyped-def]
                B, T = idx.shape
                pos = torch.arange(T, device=idx.device)
                x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
                x = self.blocks(x)
                x = self.ln_f(x)
                logits = self.head(x)
                return logits

            @torch.no_grad()
            def generate(self, idx, max_new_tokens: int, temperature: float):  # type: ignore[no-untyped-def]
                for _ in range(max_new_tokens):
                    idx_cond = idx[:, -BLOCK_SIZE:]
                    logits = self(idx_cond)
                    logits = logits[:, -1, :] / max(temperature, 1e-4)
                    probs = F.softmax(logits, dim=-1)
                    next_tok = torch.multinomial(probs, num_samples=1)
                    idx = torch.cat([idx, next_tok], dim=1)
                return idx

        model = GPT().to(device)
        try:
            ckpt = torch.load(str(checkpoint_path), map_location=device)
            if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                model.load_state_dict(ckpt["model_state_dict"])
            elif isinstance(ckpt, dict):
                model.load_state_dict(ckpt)
            else:
                return None
        except Exception:
            return None

        model.eval()
        return cls(
            model=model,
            encode=encode,
            decode=decode,
            temperature=float(temperature),
            max_new_chars=int(max_new_chars),
            device=device,
        )

    def generate(self, prompt: str) -> str:
        try:
            import torch
        except Exception:
            return ""

        p = redact_pii_like(prompt)
        idx0 = torch.tensor([self.encode(p)], dtype=torch.long, device=self.device)
        out = self.model.generate(idx0, self.max_new_chars, self.temperature)
        s = self.decode(out[0].tolist())
        # Return only the continuation (best-effort).
        if s.startswith(p):
            s = s[len(p) :]
        return s.strip()
