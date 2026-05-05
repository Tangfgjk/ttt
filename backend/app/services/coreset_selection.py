from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CoresetCandidate:
    question_id: int
    text: str
    embedding: list[float] | None = None


@dataclass(frozen=True)
class CoresetSelection:
    question_id: int
    score: float
    rank_no: int


class CoresetSelector:
    """Small dependency-free selector used until the embedding pipeline is online.

    If question embeddings exist, the selector uses them directly. Otherwise it
    builds deterministic hashed text vectors from the question stem. The
    strategies mirror the research prototype in `Strategies.py`: random,
    k-means, Facility Location, Graph Cut, and a lightweight MoE router.
    """

    def __init__(self, vector_dim: int = 64, seed: int = 42) -> None:
        self.vector_dim = vector_dim
        self.seed = seed

    def select(
        self,
        candidates: Sequence[CoresetCandidate],
        strategy: str,
        budget: int,
    ) -> list[CoresetSelection]:
        if not candidates:
            return []

        actual_budget = min(budget, len(candidates))
        vectors = [self._vector_for(candidate) for candidate in candidates]

        if strategy == "random":
            indices = self._random_sampling(len(candidates), actual_budget)
        elif strategy == "kmeans":
            indices = self._kmeans_sampling(vectors, actual_budget)
        elif strategy == "facility_location":
            indices = self._facility_location(vectors, actual_budget)
        elif strategy == "graph_cut":
            indices = self._graph_cut(vectors, actual_budget)
        elif strategy == "moe":
            indices = self._moe(vectors, actual_budget)
        else:
            raise ValueError(f"Unsupported coreset strategy: {strategy}")

        return [
            CoresetSelection(
                question_id=candidates[index].question_id,
                score=float(actual_budget - rank),
                rank_no=rank + 1,
            )
            for rank, index in enumerate(indices[:actual_budget])
        ]

    def _vector_for(self, candidate: CoresetCandidate) -> list[float]:
        if candidate.embedding:
            return self._normalize([float(value) for value in candidate.embedding])

        vector = [0.0] * self.vector_dim
        text = candidate.text or str(candidate.question_id)
        for token in self._char_ngrams(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.vector_dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        return self._normalize(vector)

    def _char_ngrams(self, text: str) -> list[str]:
        compact = "".join(text.split())
        if len(compact) <= 2:
            return [compact]
        return [compact[index : index + 3] for index in range(len(compact) - 2)]

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _random_sampling(self, total: int, budget: int) -> list[int]:
        rng = random.Random(self.seed)
        indices = list(range(total))
        rng.shuffle(indices)
        return indices[:budget]

    def _facility_location(self, vectors: list[list[float]], budget: int) -> list[int]:
        selected: list[int] = []
        remaining = set(range(len(vectors)))
        current_max = [0.0] * len(vectors)

        while remaining and len(selected) < budget:
            best_idx = -1
            best_gain = float("-inf")
            for candidate_idx in remaining:
                gain = 0.0
                for row_idx, vector in enumerate(vectors):
                    similarity = self._cosine(vector, vectors[candidate_idx])
                    gain += max(0.0, similarity - current_max[row_idx])
                if gain > best_gain:
                    best_gain = gain
                    best_idx = candidate_idx

            selected.append(best_idx)
            remaining.remove(best_idx)
            for row_idx, vector in enumerate(vectors):
                current_max[row_idx] = max(
                    current_max[row_idx],
                    self._cosine(vector, vectors[best_idx]),
                )

        return selected

    def _graph_cut(
        self,
        vectors: list[list[float]],
        budget: int,
        lambda_weight: float = 1.0,
    ) -> list[int]:
        selected: list[int] = []
        remaining = set(range(len(vectors)))
        representative = [
            sum(self._cosine(vector, other) for other in vectors) / len(vectors)
            for vector in vectors
        ]
        sim_to_selected = [0.0] * len(vectors)

        while remaining and len(selected) < budget:
            step = len(selected)
            best_idx = -1
            best_gain = float("-inf")
            for candidate_idx in remaining:
                penalty = sim_to_selected[candidate_idx] / step if step else 0.0
                gain = representative[candidate_idx] - lambda_weight * penalty
                if gain > best_gain:
                    best_gain = gain
                    best_idx = candidate_idx

            selected.append(best_idx)
            remaining.remove(best_idx)
            for row_idx, vector in enumerate(vectors):
                sim_to_selected[row_idx] += self._cosine(vector, vectors[best_idx])

        return selected

    def _kmeans_sampling(self, vectors: list[list[float]], budget: int) -> list[int]:
        if len(vectors) <= budget:
            return list(range(len(vectors)))

        rng = random.Random(self.seed)
        center_indices = self._kmeans_plus_plus(vectors, budget, rng)
        centers = [vectors[index] for index in center_indices]
        labels = [0] * len(vectors)

        for _ in range(8):
            labels = [self._nearest_center(vector, centers) for vector in vectors]
            new_centers: list[list[float]] = []
            for cluster_idx in range(budget):
                members = [vectors[i] for i, label in enumerate(labels) if label == cluster_idx]
                new_centers.append(self._mean_vector(members) if members else centers[cluster_idx])
            centers = new_centers

        selected: list[int] = []
        for cluster_idx, center in enumerate(centers):
            member_indices = [i for i, label in enumerate(labels) if label == cluster_idx]
            if not member_indices:
                continue
            selected.append(
                min(member_indices, key=lambda idx: self._euclidean(vectors[idx], center))
            )

        if len(selected) < budget:
            for idx in range(len(vectors)):
                if idx not in selected:
                    selected.append(idx)
                if len(selected) == budget:
                    break
        return selected[:budget]

    def _moe(self, vectors: list[list[float]], budget: int) -> list[int]:
        if len(vectors) <= budget:
            return list(range(len(vectors)))

        half = max(1, budget // 2)
        fl_indices = self._facility_location(vectors, half)
        selected = list(fl_indices)
        remaining_vectors = [vector for idx, vector in enumerate(vectors) if idx not in selected]
        remaining_map = [idx for idx in range(len(vectors)) if idx not in selected]
        for idx in self._graph_cut(remaining_vectors, budget - len(selected)):
            selected.append(remaining_map[idx])
        return selected[:budget]

    def _kmeans_plus_plus(
        self,
        vectors: list[list[float]],
        budget: int,
        rng: random.Random,
    ) -> list[int]:
        centers = [rng.randrange(len(vectors))]
        while len(centers) < budget:
            distances = [
                min(self._euclidean(vector, vectors[center]) for center in centers)
                for vector in vectors
            ]
            total = sum(distance * distance for distance in distances)
            if total == 0:
                break
            threshold = rng.random() * total
            cumulative = 0.0
            for idx, distance in enumerate(distances):
                cumulative += distance * distance
                if cumulative >= threshold and idx not in centers:
                    centers.append(idx)
                    break
        for idx in range(len(vectors)):
            if len(centers) == budget:
                break
            if idx not in centers:
                centers.append(idx)
        return centers[:budget]

    def _nearest_center(self, vector: list[float], centers: list[list[float]]) -> int:
        return min(range(len(centers)), key=lambda idx: self._euclidean(vector, centers[idx]))

    def _mean_vector(self, vectors: list[list[float]]) -> list[float]:
        if not vectors:
            return []
        dim = len(vectors[0])
        return [sum(vector[i] for vector in vectors) / len(vectors) for i in range(dim)]

    def _cosine(self, left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))

    def _euclidean(self, left: list[float], right: list[float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=False)))
