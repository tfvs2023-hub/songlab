"""Extract frozen per-layer embeddings from MERT or AST for every VocalSet clip.

Each clip is cut into fixed-length chunks, every chunk is embedded, and the chunk embeddings are
averaged, giving one ``[num_layers, hidden_size]`` array per clip. The result is saved as an .npz
that ``evaluate.py`` consumes.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List

import numpy as np
import torch

from vocalset import TECHNIQUES, describe, index_vocalset, load_audio

DEFAULT_CHECKPOINTS = {
    "mert": "m-a-p/MERT-v1-95M",
    "ast": "MIT/ast-finetuned-audioset-10-10-0.4593",
}
# MERT was pre-trained on ~5 s crops; AST's input window is 1024 frames (~10.24 s).
DEFAULT_CHUNK_SEC = {"mert": 5.0, "ast": 10.0}


class MertEmbedder:
    """Mean-pools every hidden layer of MERT over time (13 layers for 95M, 25 for 330M)."""

    def __init__(self, model, processor, device: torch.device) -> None:
        self.model = model.to(device).eval()
        self.processor = processor
        self.device = device
        self.sample_rate = processor.sampling_rate

    @classmethod
    def from_pretrained(cls, checkpoint: str, device: torch.device) -> "MertEmbedder":
        from transformers import AutoModel, Wav2Vec2FeatureExtractor

        model = AutoModel.from_pretrained(checkpoint, trust_remote_code=True)
        processor = Wav2Vec2FeatureExtractor.from_pretrained(checkpoint, trust_remote_code=True)
        return cls(model, processor, device)

    @torch.no_grad()
    def embed(self, wave: np.ndarray) -> np.ndarray:
        inputs = self.processor(wave, sampling_rate=self.sample_rate, return_tensors="pt").to(self.device)
        hidden = self.model(**inputs, output_hidden_states=True).hidden_states
        return torch.stack([h[0].mean(dim=0) for h in hidden]).float().cpu().numpy()


class AstEmbedder:
    """Mean-pools AST patch tokens that cover real audio (padding patches are excluded)."""

    def __init__(self, model, processor, device: torch.device) -> None:
        self.model = model.to(device).eval()
        self.processor = processor
        self.device = device
        self.sample_rate = processor.sampling_rate
        cfg = model.config
        self.freq_patches = (cfg.num_mel_bins - cfg.patch_size) // cfg.frequency_stride + 1
        self.time_patches = (cfg.max_length - cfg.patch_size) // cfg.time_stride + 1
        self.time_stride = cfg.time_stride

    @classmethod
    def from_pretrained(cls, checkpoint: str, device: torch.device) -> "AstEmbedder":
        from transformers import ASTFeatureExtractor, ASTModel

        model = ASTModel.from_pretrained(checkpoint)
        processor = ASTFeatureExtractor.from_pretrained(checkpoint)
        return cls(model, processor, device)

    def _real_time_patches(self, num_samples: int) -> int:
        # Kaldi fbank in the feature extractor: 25 ms window, 10 ms hop.
        win, hop = int(0.025 * self.sample_rate), int(0.010 * self.sample_rate)
        frames = 1 + max(num_samples - win, 0) // hop
        patches = -(-frames // self.time_stride)  # ceil
        return int(min(max(patches, 1), self.time_patches))

    @torch.no_grad()
    def embed(self, wave: np.ndarray) -> np.ndarray:
        inputs = self.processor(wave, sampling_rate=self.sample_rate, return_tensors="pt").to(self.device)
        hidden = self.model(**inputs, output_hidden_states=True).hidden_states
        keep = self._real_time_patches(len(wave))
        pooled = []
        for h in hidden:
            # Drop [CLS] and distillation tokens; patches are laid out frequency-major.
            patches = h[0, 2:].reshape(self.freq_patches, self.time_patches, -1)
            pooled.append(patches[:, :keep].mean(dim=(0, 1)))
        return torch.stack(pooled).float().cpu().numpy()


def chunk(wave: np.ndarray, sr: int, chunk_sec: float, min_chunk_sec: float) -> List[np.ndarray]:
    size = int(chunk_sec * sr)
    pieces = [wave[i : i + size] for i in range(0, len(wave), size)]
    kept = [p for p in pieces if len(p) >= int(min_chunk_sec * sr)]
    return kept or pieces[:1]


def embed_clip(embedder, wave: np.ndarray, chunk_sec: float, min_chunk_sec: float) -> np.ndarray:
    pieces = chunk(wave, embedder.sample_rate, chunk_sec, min_chunk_sec)
    return np.mean([embedder.embed(p) for p in pieces], axis=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=sorted(DEFAULT_CHECKPOINTS), required=True)
    parser.add_argument("--data-root", type=Path, required=True, help="Path to VocalSet/FULL")
    parser.add_argument("--out", type=Path, help="Output .npz (default: outputs/vocal_probe/<model>.npz)")
    parser.add_argument("--checkpoint", help="Override the Hugging Face checkpoint id")
    parser.add_argument("--chunk-sec", type=float, help="Chunk length in seconds (default: 5 for MERT, 10 for AST)")
    parser.add_argument("--min-chunk-sec", type=float, default=1.0, help="Drop trailing chunks shorter than this")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--limit", type=int, help="Only process the first N clips (smoke test)")
    args = parser.parse_args()

    checkpoint = args.checkpoint or DEFAULT_CHECKPOINTS[args.model]
    chunk_sec = args.chunk_sec or DEFAULT_CHUNK_SEC[args.model]
    out = args.out or Path("outputs/vocal_probe") / f"{args.model}.npz"
    device = torch.device(args.device)

    clips = index_vocalset(args.data_root)
    print(describe(clips))
    if args.limit:
        clips = clips[: args.limit]

    embedder_cls = MertEmbedder if args.model == "mert" else AstEmbedder
    print(f"Loading {checkpoint} on {device} ...")
    embedder = embedder_cls.from_pretrained(checkpoint, device)

    embeddings = []
    start = time.time()
    for i, clip in enumerate(clips, 1):
        wave = load_audio(clip.path, embedder.sample_rate)
        embeddings.append(embed_clip(embedder, wave, chunk_sec, args.min_chunk_sec))
        if i % 50 == 0 or i == len(clips):
            print(f"[{i}/{len(clips)}] {time.time() - start:.0f}s elapsed")

    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        embeddings=np.stack(embeddings).astype(np.float32),
        labels=np.array([c.technique for c in clips]),
        singers=np.array([c.singer for c in clips]),
        paths=np.array([str(c.path) for c in clips]),
        techniques=np.array(TECHNIQUES),
        model=args.model,
        checkpoint=checkpoint,
        chunk_sec=chunk_sec,
    )
    print(f"Saved {len(clips)} x {embeddings[0].shape} embeddings to {out}")


if __name__ == "__main__":
    main()
