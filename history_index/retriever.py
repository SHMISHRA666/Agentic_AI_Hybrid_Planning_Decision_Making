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

from .indexer import simple_embed


class HistoryRetriever:
    def __init__(self, index_dir: str = "faiss_index"):
        self.index_dir = index_dir
        self._load()

    def _load(self):
        npz_path = os.path.join(self.index_dir, 'history_index.npz')
        if os.path.exists(npz_path):
            data = np.load(npz_path, allow_pickle=True)
            self.X = data['X']
            self.meta = data['meta']
        else:
            self.X = np.zeros((0, 256), dtype=np.float32)
            self.meta = np.array([], dtype=object)

        self.faiss_idx = None
        if FAISS_AVAILABLE:
            faiss_path = os.path.join(self.index_dir, 'history.index')
            if os.path.exists(faiss_path) and self.X.shape[0] > 0:
                try:
                    self.faiss_idx = faiss.read_index(faiss_path)
                except Exception:
                    self.faiss_idx = None

    def retrieve(self, query: str, top_k: int = 3) -> List[dict]:
        if self.X.shape[0] == 0:
            return []

        q = simple_embed(query).reshape(1, -1)

        if self.faiss_idx is not None:
            sims, idxs = self.faiss_idx.search(q, min(top_k, self.X.shape[0]))
            idxs = idxs[0]
        else:
            # Cosine via dot product since vectors are normalized
            sims = self.X @ q.T  # (N, 1)
            idxs = np.argsort(-sims.ravel())[:top_k]

        results: List[dict] = []
        for i in idxs:
            try:
                meta = json.loads(str(self.meta[i]))
            except Exception:
                continue
            results.append(meta)
        return results


