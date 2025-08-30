from __future__ import annotations

from typing import List, Tuple
import os
import json

import numpy as np

try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False


def simple_embed(text: str) -> np.ndarray:
    # Lightweight deterministic embedding: bag-of-words hashed features
    # Replace with SentenceTransformers in production
    tokens = text.lower().split()
    dim = 256
    vec = np.zeros(dim, dtype=np.float32)
    for t in tokens:
        idx = hash(t) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec) or 1.0
    return vec / norm


class HistoryIndexer:
    def __init__(self, memory_base_dir: str = "memory", index_dir: str = "faiss_index"):
        self.memory_base_dir = memory_base_dir
        self.index_dir = index_dir
        os.makedirs(self.index_dir, exist_ok=True)

    def _collect_qas(self) -> List[Tuple[str, str]]:
        qas: List[Tuple[str, str]] = []
        if not os.path.exists(self.memory_base_dir):
            return qas

        for root, _dirs, files in os.walk(self.memory_base_dir):
            for f in files:
                if not f.endswith('.json'):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                except Exception:
                    continue

                # Extract (query, final_answer) pairs per session
                user_query = None
                final_answer = None
                for item in data:
                    t = item.get('type')
                    if t == 'run_metadata' and not user_query:
                        user_query = item.get('user_query') or item.get('text')
                    elif t == 'final_answer':
                        final_answer = item.get('final_answer') or item.get('text')

                if user_query and final_answer:
                    qas.append((str(user_query), str(final_answer)))

        return qas

    def build(self) -> str:
        qas = self._collect_qas()
        if not qas:
            # Create empty index file
            index_path = os.path.join(self.index_dir, 'history_index.npz')
            np.savez(index_path, X=np.zeros((0, 256), dtype=np.float32), meta=np.array([], dtype=object))
            return index_path

        X = np.vstack([simple_embed(q + "\n" + a) for q, a in qas])
        meta = np.array([json.dumps({"query": q, "answer": a}) for q, a in qas], dtype=object)

        index_path = os.path.join(self.index_dir, 'history_index.npz')
        np.savez(index_path, X=X, meta=meta)

        # Optional FAISS flat index for speed if available
        if FAISS_AVAILABLE and X.shape[0] > 0:
            faiss_path = os.path.join(self.index_dir, 'history.index')
            idx = faiss.IndexFlatIP(X.shape[1])
            idx.add(X)
            faiss.write_index(idx, faiss_path)

        return index_path

if __name__ == "__main__":
    path = HistoryIndexer().build()
    print(f"Built history index at: {path}")


