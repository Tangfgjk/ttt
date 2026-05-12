from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np


@dataclass(frozen=True)
class CoresetCandidate:
    question_id: int
    text: str
    embedding: list[float] | None = None
    created_at: datetime | None = None


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
        self.last_summary: dict[str, int | float | str] = {}

    def select(
        self,
        candidates: Sequence[CoresetCandidate],
        strategy: str,
        budget: int,
    ) -> list[CoresetSelection]:
        self.last_summary = {
            "selection_mode": "approximate_working_set",
            "strategy": strategy,
            "candidate_count": len(candidates),
            "requested_count": budget,
        }
        if not candidates:
            return []

        actual_budget = min(budget, len(candidates))

        if strategy == "random":
            indices = self._random_sampling(len(candidates), actual_budget)
            self.last_summary["working_candidate_count"] = len(candidates)
        else:
            working_indices = self._working_candidate_indices(
                total=len(candidates),
                strategy=strategy,
                budget=actual_budget,
            )
            working_candidates = [candidates[index] for index in working_indices]
            vectors = [self._vector_for(candidate) for candidate in working_candidates]
            self.last_summary["working_candidate_count"] = len(working_candidates)

            if strategy == "kmeans":
                local_indices = self._kmeans_sampling(vectors, actual_budget)
            elif strategy == "facility_location":
                local_indices = self._facility_location(vectors, actual_budget)
            elif strategy == "graph_cut":
                local_indices = self._graph_cut(vectors, actual_budget)
            elif strategy == "moe":
                local_indices = self._moe(vectors, actual_budget)
            else:
                raise ValueError(f"Unsupported coreset strategy: {strategy}")

            indices = [working_indices[index] for index in local_indices]

        return [
            CoresetSelection(
                question_id=candidates[index].question_id,
                score=float(actual_budget - rank),
                rank_no=rank + 1,
            )
            for rank, index in enumerate(indices[:actual_budget])
        ]

    def select_full_pool(
        self,
        candidates: Sequence[CoresetCandidate],
        strategy: str,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[CoresetSelection]:
        if not candidates:
            return []

        actual_budget = min(budget, len(candidates))
        if strategy == "random":
            indices = self._random_sampling(len(candidates), actual_budget)
            self.last_summary = {
                "selection_mode": "full_pool_random",
                "strategy": strategy,
                "candidate_count": len(candidates),
                "requested_count": budget,
                "working_candidate_count": len(candidates),
            }
        elif strategy == "kmeans":
            vectors = np.asarray(
                [self._vector_for(candidate) for candidate in candidates],
                dtype=np.float32,
            )
            indices = self._kmeans_sampling_full_pool(
                vectors,
                actual_budget,
                progress_callback=progress_callback,
            )
            self.last_summary = {
                "selection_mode": "full_pool_embedding",
                "strategy": strategy,
                "candidate_count": len(candidates),
                "requested_count": budget,
                "working_candidate_count": len(candidates),
                "cluster_count": actual_budget,
                "nonempty_cluster_count": len(indices),
            }
        elif strategy in {"facility_location", "graph_cut", "moe"}:
            vectors = np.asarray(
                [self._vector_for(candidate) for candidate in candidates],
                dtype=np.float32,
            )
            indices = self._hierarchical_full_pool_sampling(
                vectors,
                strategy,
                actual_budget,
                progress_callback=progress_callback,
            )
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

    def select_incremental(
        self,
        candidates: Sequence[CoresetCandidate],
        anchors: Sequence[CoresetCandidate],
        strategy: str,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[CoresetSelection]:
        if not candidates:
            self.last_summary = {
                "selection_mode": "incremental_update",
                "strategy": strategy,
                "candidate_count": 0,
                "requested_count": budget,
                "anchor_count": len(anchors),
                "working_candidate_count": 0,
            }
            return []

        actual_budget = min(budget, len(candidates))
        anchor_vectors = np.asarray(
            [self._vector_for(candidate) for candidate in anchors],
            dtype=np.float32,
        )
        new_vectors = np.asarray(
            [self._vector_for(candidate) for candidate in candidates],
            dtype=np.float32,
        )

        if strategy == "random":
            indices = self._random_sampling(len(candidates), actual_budget)
            self.last_summary = {
                "selection_mode": "incremental_random",
                "strategy": strategy,
                "candidate_count": len(candidates),
                "requested_count": budget,
                "anchor_count": len(anchors),
                "working_candidate_count": len(candidates),
            }
        else:
            indices = self._incremental_sampling(
                new_vectors,
                anchor_vectors,
                strategy,
                actual_budget,
                progress_callback=progress_callback,
            )

        return [
            CoresetSelection(
                question_id=candidates[index].question_id,
                score=float(actual_budget - rank),
                rank_no=rank + 1,
            )
            for rank, index in enumerate(indices[:actual_budget])
        ]

    def working_set_size(self, strategy: str, budget: int, total: int) -> int:
        if total <= budget:
            return total

        if strategy == "kmeans":
            subset_size = min(total, max(200, budget * 6))
        elif strategy == "moe":
            subset_size = min(total, max(180, budget * 5))
        elif strategy in {"facility_location", "graph_cut"}:
            subset_size = min(total, max(160, budget * 4))
        else:
            subset_size = total
        return min(subset_size, 800)

    def _working_candidate_indices(
        self,
        *,
        total: int,
        strategy: str,
        budget: int,
    ) -> list[int]:
        if total <= budget:
            return list(range(total))

        subset_size = self.working_set_size(strategy, budget, total)
        if subset_size >= total:
            return list(range(total))

        rng = random.Random(self.seed)
        return sorted(rng.sample(range(total), subset_size))

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

    def _kmeans_sampling_full_pool(
        self,
        vectors: np.ndarray,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
        max_iter: int = 10,
    ) -> list[int]:
        if len(vectors) <= budget:
            return list(range(len(vectors)))

        matrix = self._normalize_matrix(vectors)
        total_steps = max(budget + max_iter + 2, 1)
        step = 0

        def advance() -> None:
            nonlocal step
            step += 1
            if progress_callback is not None:
                progress_callback(min(step, total_steps), total_steps)

        centers_idx = self._kmeans_plus_plus_numpy(matrix, budget)
        centers = matrix[centers_idx].copy()
        advance()

        labels = np.zeros(len(matrix), dtype=np.int32)
        for _ in range(max_iter):
            scores = matrix @ centers.T
            labels = np.argmax(scores, axis=1).astype(np.int32)
            new_centers = centers.copy()
            for cluster_idx in range(budget):
                member_mask = labels == cluster_idx
                if not np.any(member_mask):
                    continue
                new_centers[cluster_idx] = matrix[member_mask].mean(axis=0)
            centers = self._normalize_matrix(new_centers)
            advance()

        scores = matrix @ centers.T
        labels = np.argmax(scores, axis=1).astype(np.int32)
        selected: list[int] = []
        selected_set: set[int] = set()
        cluster_scores = scores[np.arange(len(matrix)), labels]
        global_order = np.argsort(cluster_scores)[::-1].tolist()

        for cluster_idx in range(budget):
            member_indices = np.where(labels == cluster_idx)[0]
            if member_indices.size == 0:
                continue
            member_scores = scores[member_indices, cluster_idx]
            best_local = int(member_indices[int(np.argmax(member_scores))])
            if best_local not in selected_set:
                selected.append(best_local)
                selected_set.add(best_local)
            advance()

        for idx in global_order:
            if idx in selected_set:
                continue
            selected.append(int(idx))
            selected_set.add(int(idx))
            if len(selected) >= budget:
                break

        advance()
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

    def _incremental_sampling(
        self,
        new_vectors: np.ndarray,
        anchor_vectors: np.ndarray,
        strategy: str,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[int]:
        if len(new_vectors) <= budget:
            self.last_summary = {
                "selection_mode": "incremental_update",
                "strategy": strategy,
                "candidate_count": len(new_vectors),
                "requested_count": budget,
                "anchor_count": len(anchor_vectors),
                "working_candidate_count": len(new_vectors),
                "cluster_count": len(new_vectors),
                "nonempty_cluster_count": len(new_vectors),
                "largest_cluster_size": 1 if len(new_vectors) else 0,
                "smallest_cluster_size": 1 if len(new_vectors) else 0,
            }
            return list(range(len(new_vectors)))

        matrix = self._normalize_matrix(new_vectors)
        anchor_matrix = (
            self._normalize_matrix(anchor_vectors)
            if len(anchor_vectors)
            else np.empty((0, matrix.shape[1]), dtype=np.float32)
        )

        if strategy == "kmeans":
            return self._incremental_kmeans_sampling(
                matrix,
                anchor_matrix,
                budget,
                progress_callback=progress_callback,
            )
        if strategy in {"facility_location", "graph_cut", "moe"}:
            return self._incremental_hierarchical_sampling(
                matrix,
                anchor_matrix,
                strategy,
                budget,
                progress_callback=progress_callback,
            )
        raise ValueError(f"Unsupported incremental coreset strategy: {strategy}")

    def _incremental_kmeans_sampling(
        self,
        matrix: np.ndarray,
        anchor_matrix: np.ndarray,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[int]:
        cluster_count = self._hierarchical_cluster_count(len(matrix), budget)
        total_steps = max(cluster_count + 12, 1)
        step = 0

        def advance() -> None:
            nonlocal step
            step += 1
            if progress_callback is not None:
                progress_callback(min(step, total_steps), total_steps)

        labels, centers = self._partition_with_kmeans(
            matrix,
            cluster_count,
            max_iter=8,
            step_callback=advance,
        )
        sizes = np.bincount(labels, minlength=cluster_count)
        novelty_by_cluster = self._cluster_novelty_scores(centers, anchor_matrix)
        quotas = self._allocate_weighted_cluster_quotas(sizes, novelty_by_cluster, budget)
        selected = self._select_incremental_cluster_representatives(
            matrix,
            labels,
            centers,
            quotas,
            anchor_matrix,
            advance,
        )
        self._store_incremental_summary(
            strategy="kmeans",
            candidate_count=len(matrix),
            requested_count=budget,
            anchor_count=len(anchor_matrix),
            labels=labels,
            cluster_count=cluster_count,
        )
        return selected

    def _incremental_hierarchical_sampling(
        self,
        matrix: np.ndarray,
        anchor_matrix: np.ndarray,
        strategy: str,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[int]:
        cluster_count = self._hierarchical_cluster_count(len(matrix), budget)
        total_steps = max(cluster_count + 12, 1)
        step = 0

        def advance() -> None:
            nonlocal step
            step += 1
            if progress_callback is not None:
                progress_callback(min(step, total_steps), total_steps)

        labels, centers = self._partition_with_kmeans(
            matrix,
            cluster_count,
            max_iter=8,
            step_callback=advance,
        )
        sizes = np.bincount(labels, minlength=cluster_count)
        novelty_by_cluster = self._cluster_novelty_scores(centers, anchor_matrix)
        quotas = self._allocate_weighted_cluster_quotas(sizes, novelty_by_cluster, budget)
        selected: list[int] = []
        selected_set: set[int] = set()

        cluster_order = np.argsort(quotas)[::-1].tolist()
        for cluster_idx in cluster_order:
            quota = int(quotas[cluster_idx])
            if quota <= 0:
                continue
            member_indices = np.where(labels == cluster_idx)[0]
            if member_indices.size == 0:
                continue
            local_vectors = matrix[member_indices]
            local_anchors = self._nearest_anchor_subset(
                anchor_matrix,
                centers[cluster_idx],
                limit=max(8, quota * 4),
            )
            local_selected = self._cluster_local_selection_incremental(
                local_vectors,
                local_anchors,
                strategy,
                min(quota, len(member_indices)),
            )
            for local_index in local_selected:
                global_index = int(member_indices[local_index])
                if global_index in selected_set:
                    continue
                selected.append(global_index)
                selected_set.add(global_index)
                if len(selected) >= budget:
                    break
            advance()
            if len(selected) >= budget:
                break

        if len(selected) < budget:
            fallback_order = self._incremental_fallback_order(matrix, anchor_matrix, centers)
            for idx in fallback_order:
                if idx in selected_set:
                    continue
                selected.append(idx)
                selected_set.add(idx)
                if len(selected) >= budget:
                    break

        self._store_incremental_summary(
            strategy=strategy,
            candidate_count=len(matrix),
            requested_count=budget,
            anchor_count=len(anchor_matrix),
            labels=labels,
            cluster_count=cluster_count,
        )
        return selected[:budget]

    def _cluster_novelty_scores(
        self,
        centers: np.ndarray,
        anchor_matrix: np.ndarray,
    ) -> np.ndarray:
        if len(anchor_matrix) == 0:
            return np.ones(len(centers), dtype=np.float32)
        max_sim = (centers @ anchor_matrix.T).max(axis=1)
        novelty = np.clip(1.0 - max_sim, 0.05, 1.0)
        return novelty.astype(np.float32)

    def _allocate_weighted_cluster_quotas(
        self,
        sizes: np.ndarray,
        weights: np.ndarray,
        budget: int,
    ) -> np.ndarray:
        weighted_sizes = sizes.astype(np.float64) * weights.astype(np.float64)
        if weighted_sizes.sum() <= 0:
            return self._allocate_cluster_quotas(sizes, budget)
        quotas = np.zeros(len(sizes), dtype=np.int32)
        ideal = weighted_sizes * float(budget) / float(weighted_sizes.sum())
        quotas = np.floor(ideal).astype(np.int32)
        remaining = budget - int(quotas.sum())
        if remaining > 0:
            residual_order = np.argsort(ideal - quotas)[::-1]
            for cluster_idx in residual_order:
                if sizes[cluster_idx] <= 0:
                    continue
                quotas[cluster_idx] += 1
                remaining -= 1
                if remaining <= 0:
                    break
        if int(quotas.sum()) == 0:
            return self._allocate_cluster_quotas(sizes, budget)
        return quotas

    def _select_incremental_cluster_representatives(
        self,
        matrix: np.ndarray,
        labels: np.ndarray,
        centers: np.ndarray,
        quotas: np.ndarray,
        anchor_matrix: np.ndarray,
        advance: Callable[[], None],
    ) -> list[int]:
        selected: list[int] = []
        selected_set: set[int] = set()
        cluster_order = np.argsort(quotas)[::-1].tolist()
        for cluster_idx in cluster_order:
            quota = int(quotas[cluster_idx])
            if quota <= 0:
                continue
            member_indices = np.where(labels == cluster_idx)[0]
            if member_indices.size == 0:
                continue
            member_vectors = matrix[member_indices]
            center_scores = member_vectors @ centers[cluster_idx]
            novelty_scores = self._vector_novelty_scores(member_vectors, anchor_matrix)
            ranking = np.argsort(0.7 * center_scores + 0.3 * novelty_scores)[::-1].tolist()
            for local_pos in ranking:
                global_index = int(member_indices[int(local_pos)])
                if global_index in selected_set:
                    continue
                selected.append(global_index)
                selected_set.add(global_index)
                if len([idx for idx in selected if labels[idx] == cluster_idx]) >= min(
                    quota, len(member_indices)
                ):
                    break
            advance()
        return selected

    def _vector_novelty_scores(
        self,
        vectors: np.ndarray,
        anchor_matrix: np.ndarray,
    ) -> np.ndarray:
        if len(anchor_matrix) == 0:
            return np.ones(len(vectors), dtype=np.float32)
        return np.clip(1.0 - (vectors @ anchor_matrix.T).max(axis=1), 0.0, 1.0).astype(
            np.float32
        )

    def _nearest_anchor_subset(
        self,
        anchor_matrix: np.ndarray,
        center: np.ndarray,
        *,
        limit: int,
    ) -> np.ndarray:
        if len(anchor_matrix) == 0 or len(anchor_matrix) <= limit:
            return anchor_matrix
        scores = anchor_matrix @ center
        order = np.argsort(scores)[::-1][:limit]
        return anchor_matrix[order]

    def _cluster_local_selection_incremental(
        self,
        local_vectors: np.ndarray,
        local_anchors: np.ndarray,
        strategy: str,
        budget: int,
    ) -> list[int]:
        if len(local_vectors) <= budget:
            return list(range(len(local_vectors)))
        if budget <= 0:
            return []
        if strategy == "facility_location":
            return self._facility_location_numpy(local_vectors, budget, reference_vectors=local_anchors)
        if strategy == "graph_cut":
            return self._graph_cut_numpy(local_vectors, budget, reference_vectors=local_anchors)
        if strategy == "moe":
            half = max(1, budget // 2)
            first = self._facility_location_numpy(
                local_vectors,
                min(half, budget),
                reference_vectors=local_anchors,
            )
            first_set = set(first)
            remaining = [idx for idx in range(len(local_vectors)) if idx not in first_set]
            if len(first) >= budget or not remaining:
                return first[:budget]
            second_local = self._graph_cut_numpy(
                local_vectors[remaining],
                budget - len(first),
                reference_vectors=local_anchors,
            )
            return first + [remaining[idx] for idx in second_local]
        raise ValueError(f"Unsupported incremental local strategy: {strategy}")

    def _incremental_fallback_order(
        self,
        matrix: np.ndarray,
        anchor_matrix: np.ndarray,
        centers: np.ndarray,
    ) -> list[int]:
        center_fit = (matrix @ centers.T).max(axis=1)
        novelty = self._vector_novelty_scores(matrix, anchor_matrix)
        combined = 0.55 * novelty + 0.45 * center_fit
        return [int(idx) for idx in np.argsort(combined)[::-1].tolist()]

    def _store_incremental_summary(
        self,
        *,
        strategy: str,
        candidate_count: int,
        requested_count: int,
        anchor_count: int,
        labels: np.ndarray,
        cluster_count: int,
    ) -> None:
        sizes = np.bincount(labels, minlength=cluster_count)
        nonempty_sizes = [int(size) for size in sizes.tolist() if size > 0]
        self.last_summary = {
            "selection_mode": "incremental_update",
            "strategy": strategy,
            "candidate_count": candidate_count,
            "requested_count": requested_count,
            "anchor_count": anchor_count,
            "working_candidate_count": candidate_count,
            "cluster_count": cluster_count,
            "nonempty_cluster_count": int(np.count_nonzero(sizes)),
            "largest_cluster_size": max(nonempty_sizes, default=0),
            "smallest_cluster_size": min(nonempty_sizes, default=0),
        }

    def _hierarchical_full_pool_sampling(
        self,
        vectors: np.ndarray,
        strategy: str,
        budget: int,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[int]:
        if len(vectors) <= budget:
            return list(range(len(vectors)))

        matrix = self._normalize_matrix(vectors)
        cluster_count = self._hierarchical_cluster_count(len(matrix), budget)
        total_steps = max(cluster_count + 12, 1)
        step = 0

        def advance() -> None:
            nonlocal step
            step += 1
            if progress_callback is not None:
                progress_callback(min(step, total_steps), total_steps)

        labels, centers = self._partition_with_kmeans(
            matrix,
            cluster_count,
            max_iter=8,
            step_callback=advance,
        )
        sizes = np.bincount(labels, minlength=cluster_count)
        quotas = self._allocate_cluster_quotas(sizes, budget)

        selected: list[int] = []
        selected_set: set[int] = set()
        nonempty_cluster_count = int(np.count_nonzero(sizes))
        nonempty_sizes = [int(size) for size in sizes.tolist() if size > 0]

        cluster_order = np.argsort(quotas)[::-1].tolist()
        for cluster_idx in cluster_order:
            quota = int(quotas[cluster_idx])
            if quota <= 0:
                continue
            member_indices = np.where(labels == cluster_idx)[0]
            if member_indices.size == 0:
                continue
            local_vectors = matrix[member_indices]
            local_selected = self._cluster_local_selection(
                local_vectors,
                strategy,
                min(quota, len(member_indices)),
            )
            for local_index in local_selected:
                global_index = int(member_indices[local_index])
                if global_index in selected_set:
                    continue
                selected.append(global_index)
                selected_set.add(global_index)
                if len(selected) >= budget:
                    break
            advance()
            if len(selected) >= budget:
                break

        if len(selected) < budget:
            fallback_order = np.argsort((matrix @ centers.T).max(axis=1))[::-1].tolist()
            for idx in fallback_order:
                idx = int(idx)
                if idx in selected_set:
                    continue
                selected.append(idx)
                selected_set.add(idx)
                if len(selected) >= budget:
                    break

        self.last_summary = {
            "selection_mode": "hierarchical_full_pool",
            "strategy": strategy,
            "candidate_count": len(vectors),
            "requested_count": budget,
            "working_candidate_count": len(vectors),
            "cluster_count": cluster_count,
            "nonempty_cluster_count": nonempty_cluster_count,
            "largest_cluster_size": max(nonempty_sizes, default=0),
            "smallest_cluster_size": min(nonempty_sizes, default=0),
        }
        return selected[:budget]

    def _hierarchical_cluster_count(self, total: int, budget: int) -> int:
        target = max(budget * 4, 24)
        return min(total, max(budget, min(target, 256)))

    def _partition_with_kmeans(
        self,
        vectors: np.ndarray,
        cluster_count: int,
        *,
        max_iter: int,
        step_callback: Callable[[], None] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if len(vectors) <= cluster_count:
            labels = np.arange(len(vectors), dtype=np.int32)
            centers = vectors.copy()
            return labels, centers

        center_indices = self._kmeans_plus_plus_numpy(vectors, cluster_count)
        centers = vectors[center_indices].copy()
        labels = np.zeros(len(vectors), dtype=np.int32)
        if step_callback is not None:
            step_callback()

        for _ in range(max_iter):
            scores = vectors @ centers.T
            labels = np.argmax(scores, axis=1).astype(np.int32)
            new_centers = centers.copy()
            for cluster_idx in range(cluster_count):
                member_mask = labels == cluster_idx
                if not np.any(member_mask):
                    continue
                new_centers[cluster_idx] = vectors[member_mask].mean(axis=0)
            centers = self._normalize_matrix(new_centers)
            if step_callback is not None:
                step_callback()
        return labels, centers

    def _allocate_cluster_quotas(self, sizes: np.ndarray, budget: int) -> np.ndarray:
        quotas = np.zeros(len(sizes), dtype=np.int32)
        total = int(sizes.sum())
        if total <= 0 or budget <= 0:
            return quotas

        ideal = sizes.astype(np.float64) * float(budget) / float(total)
        quotas = np.floor(ideal).astype(np.int32)
        remaining = budget - int(quotas.sum())

        if remaining > 0:
            residual_order = np.argsort(ideal - quotas)[::-1]
            for cluster_idx in residual_order:
                if sizes[cluster_idx] <= 0:
                    continue
                quotas[cluster_idx] += 1
                remaining -= 1
                if remaining <= 0:
                    break

        if int(quotas.sum()) == 0:
            size_order = np.argsort(sizes)[::-1]
            for cluster_idx in size_order[:budget]:
                if sizes[cluster_idx] <= 0:
                    continue
                quotas[cluster_idx] = 1
        return quotas

    def _cluster_local_selection(
        self,
        local_vectors: np.ndarray,
        strategy: str,
        budget: int,
    ) -> list[int]:
        if len(local_vectors) <= budget:
            return list(range(len(local_vectors)))
        if budget <= 0:
            return []

        if strategy == "facility_location":
            return self._facility_location_numpy(local_vectors, budget)
        if strategy == "graph_cut":
            return self._graph_cut_numpy(local_vectors, budget)
        if strategy == "moe":
            half = max(1, budget // 2)
            first = self._facility_location_numpy(local_vectors, min(half, budget))
            remaining = [idx for idx in range(len(local_vectors)) if idx not in set(first)]
            if len(first) >= budget or not remaining:
                return first[:budget]
            second_local = self._graph_cut_numpy(
                local_vectors[remaining],
                budget - len(first),
            )
            return first + [remaining[idx] for idx in second_local]
        raise ValueError(f"Unsupported hierarchical strategy: {strategy}")

    def _facility_location_numpy(
        self,
        vectors: np.ndarray,
        budget: int,
        *,
        reference_vectors: np.ndarray | None = None,
    ) -> list[int]:
        similarities = vectors @ vectors.T
        current_max = np.zeros(len(vectors), dtype=np.float32)
        if reference_vectors is not None and len(reference_vectors) > 0:
            current_max = np.maximum(
                current_max,
                (vectors @ reference_vectors.T).max(axis=1).astype(np.float32),
            )
        selected: list[int] = []
        selected_mask = np.zeros(len(vectors), dtype=bool)

        for _ in range(min(budget, len(vectors))):
            gains = np.maximum(similarities - current_max[:, None], 0.0).sum(axis=0)
            gains[selected_mask] = -np.inf
            best_idx = int(np.argmax(gains))
            if not np.isfinite(gains[best_idx]):
                break
            selected.append(best_idx)
            selected_mask[best_idx] = True
            current_max = np.maximum(current_max, similarities[:, best_idx])
        return selected

    def _graph_cut_numpy(
        self,
        vectors: np.ndarray,
        budget: int,
        *,
        lambda_weight: float = 1.0,
        reference_vectors: np.ndarray | None = None,
    ) -> list[int]:
        similarities = vectors @ vectors.T
        representative = similarities.mean(axis=1)
        if reference_vectors is not None and len(reference_vectors) > 0:
            representative = representative + 0.35 * (
                1.0 - (vectors @ reference_vectors.T).max(axis=1)
            )
        sim_to_selected = np.zeros(len(vectors), dtype=np.float32)
        selected: list[int] = []
        selected_mask = np.zeros(len(vectors), dtype=bool)

        for step in range(min(budget, len(vectors))):
            penalty = sim_to_selected / step if step else 0.0
            gains = representative - lambda_weight * penalty
            gains[selected_mask] = -np.inf
            best_idx = int(np.argmax(gains))
            if not np.isfinite(gains[best_idx]):
                break
            selected.append(best_idx)
            selected_mask[best_idx] = True
            sim_to_selected += similarities[:, best_idx]
        return selected

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

    def _kmeans_plus_plus_numpy(self, vectors: np.ndarray, budget: int) -> list[int]:
        rng = np.random.default_rng(self.seed)
        first_center = int(rng.integers(0, len(vectors)))
        centers = [first_center]
        min_dist_sq = self._distance_sq_to_center(vectors, vectors[first_center])

        while len(centers) < budget:
            total = float(min_dist_sq.sum())
            if total <= 0:
                break
            threshold = float(rng.random()) * total
            cumulative = float(np.cumsum(min_dist_sq).searchsorted(threshold, side="left"))
            candidate = min(int(cumulative), len(vectors) - 1)
            if candidate in centers:
                remaining = [idx for idx in range(len(vectors)) if idx not in centers]
                if not remaining:
                    break
                candidate = remaining[0]
            centers.append(candidate)
            min_dist_sq = np.minimum(
                min_dist_sq,
                self._distance_sq_to_center(vectors, vectors[candidate]),
            )

        if len(centers) < budget:
            for idx in range(len(vectors)):
                if idx not in centers:
                    centers.append(idx)
                if len(centers) >= budget:
                    break
        return centers[:budget]

    def _distance_sq_to_center(self, vectors: np.ndarray, center: np.ndarray) -> np.ndarray:
        similarities = vectors @ center
        return np.clip(2.0 - 2.0 * similarities, 0.0, None)

    def _normalize_matrix(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

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
