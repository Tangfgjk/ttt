# Coreset Selection 系统设计建议

## 1. 现有实验数据分析

### 1.1 已有实验结果概览（来自 `4.7.xlsx`）

| 算法 | Size | CoverageRadius↓ | 90th_radius↓ | AMS↑ | Redundancy↓ | CRR↑ | PCA_ratio→1.0 | MMD↓ |
|-----|------|-----------------|--------------|------|-------------|------|---------------|------|
| herding | 89 | 16.63 | 12.22 | 0.887 | 0.756 | 15.91 | 0.856 | **0.037** |
| k-center | 92 | 15.40 | 13.16 | 0.842 | **0.613** | **17.41** | 0.717 | 0.196 |
| FL | 89 | 15.82 | 11.56 | 0.907 | 0.778 | 15.80 | 0.971 | 0.070 |
| GC | 91 | 15.82 | 11.52 | 0.907 | 0.777 | 15.14 | 0.969 | 0.068 |
| ID | 89 | 15.73 | 12.14 | 0.872 | 0.713 | 16.58 | 0.792 | 0.132 |
| **k-means** | **93** | **15.50** | **11.26** | **0.909** | 0.769 | 14.68 | **0.981** | 0.058 |
| random | 92 | 16.40 | 12.04 | 0.890 | 0.730 | 15.48 | 1.018 | 0.048 |

### 1.2 关键洞察

- **k-means**：覆盖稳健性最好（90th_radius=11.26），代表性强（AMS=0.909），语义结构最完整（PCA_ratio=0.981），是**综合实力最强的 baseline**。
- **herding**：分布相似性最佳（MMD=0.037），统计学上最"像"全集，但语义结构保持一般（PCA_ratio=0.856）。
- **FL/GC**（子模函数）：代表性极强（AMS>0.90），语义结构完整，但冗余度较高（~0.78），容易选入"换皮题"。
- **k-center**：冗余度最低（0.613），差异化最大，但分布偏离严重（MMD=0.196），容易选入边缘"怪题"。
- **random**：MMD 和 PCA_ratio 表现极佳，证明了随机采样在统计上的天然优势，仍是强 baseline。

---

## 2. Coreset 系统总体架构设计

### 2.1 核心设计思想

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Coreset Selection 系统                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   输入层                                                                     │
│   ├── 嵌入向量 (RoBERTa / LLM / Sentence-BERT)  [N_pool, D]                │
│   ├── 模型预测输出 (用于不确定性方法)         [N_pool, C]                   │
│   ├── 已标注样本索引 (用于增量更新)            [N_labeled]                  │
│   └── 业务过滤规则 (年级、题型、排除集)                                     │
│                                                                             │
│   算法层 (插件化，可插拔)                                                     │
│   ├── 几何方法: Herding, K-Center, K-Means, ...                             │
│   ├── 子模方法: Facility Location, Graph Cut, ...                           │
│   ├── 不确定方法: Entropy, Margin, Least Confidence                         │
│   ├── 损失方法: Forgetting, GraNd, EL2N                                    │
│   ├── 梯度方法: CRAIG, GradMatch                                           │
│   └── 混合方法: [未来扩展] 几何+不确定加权, 多目标优化...                     │
│                                                                             │
│   融合层 (多策略集成)                                                         │
│   ├── 单算法选择 (管理员配置)                                                │
│   ├── 多算法投票 (加权平均分数)                                              │
│   └── 动态切换 (根据标注阶段自动选择最优算法)                                 │
│                                                                             │
│   输出层                                                                     │
│   ├── 推荐试题列表 (Top-K)                                                   │
│   ├── 每个样本的选择分数                                                     │
│   └── 算法质量评估指标 (CoverageRadius, AMS, MMD, ...)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 为什么采用插件化架构

1. **研究迭代需求**：Coreset 是活跃研究领域，新方法层出不穷（论文中列举了 15+ 种方法）
2. **场景适配性**：不同标注阶段适合不同算法（冷启动 vs. 有模型后）
3. **可对比实验**：需要方便地 A/B test 不同算法的效果
4. **增量改进**：新算法可直接接入现有流水线，无需改动上下游

---

## 3. 算法实现策略建议

### 3.1 推荐默认算法组合（分阶段）

| 阶段 | 已标注样本数 | 推荐算法 | 理由 |
|-----|------------|---------|------|
| **冷启动** | 0 ~ 300 | k-means / herding | 无模型时，纯几何方法最有效。k-means 综合指标最优，herding 分布最稳。 |
| **成长期** | 300 ~ 1500 | k-means + Uncertainty (混合) | 已有初步模型，可结合几何覆盖+不确定性，优先选择边界样本。 |
| **成熟期** | 1500+ | FL/GC + Uncertainty | 模型较稳定后，子模函数的代表性优势显现，结合不确定性精调。 |
| **全量验证** | 全量标注 | random | 作为最终 baseline 对照，验证主动学习是否真正有效。 |

### 3.2 混合策略设计（Hybrid Coreset）

```python
class HybridCoresetSelector(BaseCoresetSelector):
    """
    混合 Coreset 选择器：结合多种算法的分数，加权融合。
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.selectors = [
            CoresetAlgorithmFactory.get("kmeans"),
            CoresetAlgorithmFactory.get("herding"),
        ]
        self.weights = self.params.get("weights", [0.6, 0.4])
        self.uncertainty_threshold = self.params.get("uncertainty_threshold", 0.5)
    
    def select(self, pool_embeddings, pool_ids, labeled_embeddings=None,
               labeled_ids=None, model_outputs=None, n_select=10):
        
        # 1. 获取各算法的归一化分数
        all_scores = []
        for selector in self.selectors:
            scores = selector.score(pool_embeddings, labeled_embeddings, model_outputs)
            # Min-Max 归一化到 [0, 1]
            scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
            all_scores.append(scores)
        
        # 2. 加权融合
        fused_scores = np.zeros(len(pool_embeddings))
        for scores, w in zip(all_scores, self.weights):
            fused_scores += w * scores
        
        # 3. 如果有模型输出，加入不确定性奖励
        if model_outputs is not None:
            uncertainty_selector = CoresetAlgorithmFactory.get("uncertainty")
            uncertainty_scores = uncertainty_selector.score(
                pool_embeddings, model_outputs=model_outputs
            )
            uncertainty_scores = (uncertainty_scores - uncertainty_scores.min()) / \
                                  (uncertainty_scores.max() - uncertainty_scores.min() + 1e-10)
            fused_scores = 0.7 * fused_scores + 0.3 * uncertainty_scores
        
        # 4. 选择 Top-K
        top_k = np.argsort(fused_scores)[-n_select:][::-1]
        return CoresetSelectionResult(
            selected_indices=top_k,
            scores=fused_scores,
            algorithm_name="hybrid",
            metadata={
                "component_scores": [s.tolist() for s in all_scores],
                "weights": self.weights
            }
        )
```

### 3.3 增量更新策略

由于系统需要**增量式交互标注**，全量重算 4 万题的 Coreset 在性能上不可接受。建议实现以下增量策略：

| 算法 | 增量策略 | 复杂度 |
|-----|---------|--------|
| **Herding** | 新标注样本加入后，更新全集均值，从剩余池中贪心补选 | O(N_pool) |
| **K-Means** | 仅重新分配受影响的簇，若簇中心变化大则局部重选 | O(k * N_local) |
| **K-Center** | 新标注样本若成为新中心，更新覆盖半径，移除被覆盖点 | O(N_pool) |
| **Uncertainty** | 模型重训后重新 inference 全池，但可用缓存加速 | O(N_pool * forward) |
| **FL/GC** | 子模函数贪心增量：维护边际增益缓存，增量更新 | O(N_pool * k) |

### 3.4 实时性保障

- **预计算嵌入**：全量 4 万题的 RoBERTa 嵌入一次性计算，存储于 pgvector/Redis
- **Faiss 索引**：构建 IVF 或 HNSW 索引，支持快速近邻搜索（K-Means、K-Center 依赖）
- **异步重算**：标注事件触发后，Coreset 重算在后台 Celery 任务中执行，前端轮询获取新推荐
- **缓存策略**：推荐结果按用户缓存 5-10 分钟，避免频繁重算

---

## 4. 算法质量监控与自动调优

### 4.1 在线评估指标

系统应持续计算以下指标，用于监控 Coreset 质量：

```python
class CoresetMetricsEvaluator:
    """
    Coreset 质量在线评估器。
    参考论文和实验中的评估维度。
    """
    
    def evaluate(self, 
                 full_embeddings: np.ndarray,
                 selected_embeddings: np.ndarray,
                 selected_indices: np.ndarray) -> dict:
        
        metrics = {}
        
        # 1. CoverageRadius (覆盖半径) - 越小越好
        # 全集中最远样本到核心集的最小距离
        dist_matrix = cdist(full_embeddings, selected_embeddings)
        min_distances = np.min(dist_matrix, axis=1)
        metrics["coverage_radius"] = float(np.max(min_distances))
        metrics["90th_radius"] = float(np.percentile(min_distances, 90))
        
        # 2. AMS (Average Maximum Similarity) - 越高越好
        # 全集样本与核心集的最大相似度均值
        similarities = 1 / (1 + dist_matrix)  # 距离转相似度
        metrics["ams"] = float(np.mean(np.max(similarities, axis=1)))
        
        # 3. Redundancy (冗余度) - 越低越好
        # 核心集内部的平均两两相似度
        if len(selected_embeddings) > 1:
            internal_dist = cdist(selected_embeddings, selected_embeddings)
            np.fill_diagonal(internal_dist, np.inf)
            internal_sim = 1 / (1 + internal_dist)
            metrics["redundancy"] = float(np.mean(internal_sim[np.isfinite(internal_sim)]))
        else:
            metrics["redundancy"] = 0.0
        
        # 4. CRR (Coverage / Redundancy Ratio) - 越高越好
        metrics["crr"] = metrics["ams"] / (metrics["redundancy"] + 1e-10)
        
        # 5. PCA_ratio (语义结构保持) - 越接近 1.0 越好
        # 核心集前 k 个主成分方差占比 vs 全集
        from sklearn.decomposition import PCA
        pca_full = PCA(n_components=10).fit(full_embeddings)
        pca_sel = PCA(n_components=min(10, len(selected_embeddings)-1)).fit(selected_embeddings)
        var_full = np.sum(pca_full.explained_variance_ratio_)
        var_sel = np.sum(pca_sel.explained_variance_ratio_)
        metrics["pca_ratio"] = float(var_sel / var_full) if var_full > 0 else 0.0
        
        # 6. MMD (最大均值差异) - 越低越好
        # 使用 RBF 核估计分布差异
        metrics["mmd"] = float(self._compute_mmd(full_embeddings, selected_embeddings))
        
        return metrics
    
    def _compute_mmd(self, X, Y, gamma=1.0):
        """计算 RBF-MMD"""
        from sklearn.metrics.pairwise import rbf_kernel
        Kxx = rbf_kernel(X, X, gamma)
        Kyy = rbf_kernel(Y, Y, gamma)
        Kxy = rbf_kernel(X, Y, gamma)
        mmd = np.mean(Kxx) + np.mean(Kyy) - 2 * np.mean(Kxy)
        return max(0, mmd) ** 0.5
```

### 4.2 自动算法选择（AutoML for Coreset）

```python
class AdaptiveCoresetSelector(BaseCoresetSelector):
    """
    自适应 Coreset 选择器：根据当前数据状态和算法历史表现，
    动态选择最优算法或组合权重。
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.available_selectors = [
            "kmeans", "herding", "fl", "gc", "uncertainty"
        ]
        self.performance_history = {}  # 记录各算法的历史表现
    
    def select(self, pool_embeddings, pool_ids, labeled_embeddings=None,
               labeled_ids=None, model_outputs=None, n_select=10):
        
        # 1. 判断当前阶段
        n_labeled = len(labeled_ids) if labeled_ids else 0
        
        # 2. 根据阶段和表现历史选择算法
        if n_labeled < 300:
            algorithm = "kmeans"
        elif n_labeled < 1500:
            # 选择历史表现最好的算法
            algorithm = self._select_best_algorithm_from_history()
        else:
            algorithm = "fl"  # 成熟期优先子模函数
        
        # 3. 执行选择
        selector = CoresetAlgorithmFactory.get(algorithm)
        return selector.select(pool_embeddings, pool_ids, labeled_embeddings,
                               labeled_ids, model_outputs, n_select)
    
    def _select_best_algorithm_from_history(self):
        """基于历史训练任务的表现选择最优算法"""
        if not self.performance_history:
            return "kmeans"
        # 按 F1 提升幅度排序
        best_algo = max(self.performance_history, 
                       key=lambda a: self.performance_history[a].get("f1_improvement", 0))
        return best_algo
    
    def report_performance(self, algorithm: str, metrics: dict):
        """训练完成后汇报算法表现，更新历史记录"""
        self.performance_history[algorithm] = metrics
```

---

## 5. 与模型训练的闭环设计

### 5.1 主动学习闭环

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
            ┌───────────────┐                     ┌───────────────┐
            │   未标注池     │                     │   已标注集     │
            │   (40,000)    │                     │   (N labeled) │
            └───────┬───────┘                     └───────┬───────┘
                    │                                     │
                    │ Coreset 选择                        │ 模型训练
                    ▼                                     ▼
            ┌───────────────┐                     ┌───────────────┐
            │  推荐 Top-K   │◄────────────────────│  训练好的模型  │
            │  供标注员标注  │                     │  (RoBERTa+Head)│
            └───────────────┘                     └───────────────┘
                    │                                     ▲
                    │ 标注完成                            │
                    │ (人 in the loop)                    │
                    └─────────────────────────────────────┘
```

### 5.2 触发训练的条件

| 条件 | 说明 |
|-----|------|
| **定时触发** | 每新增 100 道 COMPLETED 试题，自动触发训练 |
| **手动触发** | 管理员在训练页面点击"启动训练" |
| **事件触发** | 标注达到阈值时，EventBus 通知 TrainingService |

### 5.3 实验对比设计

为了验证 Coreset 主动学习的效果，系统应支持以下对比实验：

| 实验组 | 选择策略 | 目的 |
|-------|---------|------|
| **实验组 A** | Herding Coreset | 验证分布匹配型策略 |
| **实验组 B** | K-Means Coreset | 验证几何覆盖型策略 |
| **实验组 C** | Uncertainty + K-Means 混合 | 验证混合策略 |
| **对照组** | Random 采样 | 验证是否优于随机 |

每组实验在相同的样本量递增序列下进行（如 100, 200, 300, ..., 2000），记录 F1、等级准确率、素养检出率，绘制主动学习曲线。

---

## 6. 未来扩展方向

| 方向 | 描述 | 优先级 |
|-----|------|--------|
| **多目标优化 Coreset** | 同时优化覆盖、多样性、不确定性，用 Pareto 前沿选择 | 高 |
| **对比学习嵌入** | 用 SimCLR/SimCSE 替代 RoBERTa，获取更有判别性的嵌入 | 中 |
| **LLM-as-Annotator** | 用 GPT-4/Claude 预标注，人工审核修正，加速冷启动 | 中 |
| **跨任务迁移** | 将核心素养标注的 Coreset 策略迁移到知识点标注任务 | 低 |
| **在线学习** | 模型每收到一批标注就增量更新，而非全量重训 | 中 |

---

## 7. 实现 Checklist

- [ ] 实现 `BaseCoresetSelector` 抽象接口
- [ ] 实现算法注册装饰器 `@CoresetAlgorithmFactory.register`
- [ ] 实现至少 5 种基础算法：K-Means, Herding, FL, GC, Uncertainty
- [ ] 实现 `CoresetMetricsEvaluator` 质量评估模块
- [ ] 集成 Faiss 加速近邻搜索
- [ ] 实现增量更新机制（至少 Herding 和 K-Means）
- [ ] 实现混合策略 `HybridCoresetSelector`
- [ ] 实现自适应选择 `AdaptiveCoresetSelector`
- [ ] 对接训练服务，形成主动学习闭环
- [ ] 在管理后台展示 Coreset 质量指标仪表盘
