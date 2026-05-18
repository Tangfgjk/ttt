# V8-CoreSet 真正增量更新功能设计

## 1. 背景

当前系统中的 CoreSet 增量更新逻辑容易被理解为：

```text
只从新导入的未标注题中选择 count 道题
```

这个语义不符合主动学习中的 CoreSet 增量更新目标。

更合理的目标应该是：

```text
新未标注题加入后，当前未标注题池整体发生变化。
系统仍然应该从当前全部未标注题池中选择 count 道代表题，
只是计算过程尽量复用上一次 CoreSet 保存的算法状态，避免全量重算。
```

也就是说：

```text
选题对象 = 当前全部未标注题
增量对象 = 算法状态与中间结构
```

不是：

```text
选题对象 = 新增题
```

## 2. 典型场景

假设第一次运行 CoreSet 时：

```text
未标注题池：40000 道
选题数：400 道
运行方式：K-Means 全量选题
结果：从 40000 道题中选出 400 道进入待标注池
```

这 400 道题进入标注流程后，剩余未标注池约为：

```text
39600 道
```

之后又导入了：

```text
10000 道新未标注题
```

当前未标注池变成：

```text
39600 + 10000 = 49600 道
```

此时再次运行 CoreSet，正确目标应该是：

```text
从当前 49600 道未标注题中选择 400 道
```

而不是：

```text
只从新增的 10000 道题中选择 400 道
```

## 3. 全量选题与增量更新的区别

全量选题：

```text
候选范围：当前全部未标注题
计算方式：重新计算或重新读取全部候选题向量，重新构建聚类/相似度/覆盖关系
输出结果：从当前全部未标注题中选出 count 道题
适用场景：第一次运行某个算法，或需要彻底重算
```

增量更新选题：

```text
候选范围：当前全部未标注题
计算方式：复用上一次同算法保存的中间状态，只处理新增题和受影响的局部结构
输出结果：仍然从当前全部未标注题中选出 count 道题
适用场景：同一算法已有基线，且导入了新的未标注题
```

两者的区别不在输出范围，而在计算方式：

```text
全量 = 从零重建全池结构
增量 = 复用旧结构并局部更新
```

## 4. 核心原则

### 4.1 选题范围必须是当前全池

无论全量还是增量，最终候选范围都应该是：

```text
当前全部未标注题
```

需要排除的题包括：

```text
已进入待标注池的题
领取中的题
已提交/已完成标注的题
被撤回之外仍处于非未标注状态的题
缺少有效内容或缺少可用 embedding 的题
```

### 4.2 增量基线必须按算法隔离

不同算法的中间状态不能混用。

例如：

```text
K-Means 全量基线不能用于 Graph Cut 增量
Facility Location 全量基线不能用于 K-Means 增量
```

因为不同算法依赖的状态完全不同：

```text
K-Means：聚类中心、簇分配、簇统计
Facility Location：覆盖关系、相似度缓存、边际收益
Graph Cut：近邻图、边权、局部收益缓存
```

系统规则应为：

```text
如果当前算法没有自己的增量基线，必须先运行该算法的全量选题。
```

### 4.3 增量基线还应匹配关键配置

增量基线至少需要匹配：

```text
strategy：选题算法
data_scope：候选范围
embedding_model_code：embedding 模型版本
```

建议同时记录并用于提示：

```text
requested_count：选题数
selection_mode：向量/回退模式
algorithm_params：算法参数
```

如果 embedding 模型变更，历史向量空间已经不同，不能直接复用旧算法状态。

## 5. 各选题策略的增量更新思路

### 5.1 Random

Random 不依赖复杂中间状态。

全量和增量都可以直接从当前全部未标注题中随机抽取：

```text
current_pool -> random sample count
```

需要保存：

```text
随机种子
候选池快照
选中题 ID
```

Random 的增量优化价值较低，主要保持语义一致即可。

### 5.2 K-Means 覆盖

全量：

```text
读取全部候选题 embedding
对当前全池做 K-Means
每个簇选择距离中心最近的题
```

增量：

```text
复用上次的聚类中心和簇统计
只处理新增未标注题的 embedding
将新增题分配到最近的旧簇
更新受影响簇的中心和统计量
必要时对漂移较大的簇局部重聚类
最后从当前全部未标注题中重新选择代表题
```

需要保存：

```text
cluster_centers
question_cluster_assignments
cluster_sizes
cluster_representatives
embedding_model_code
snapshot_created_before
pool_question_ids 或可重建的池快照条件
```

### 5.3 K-Center

全量：

```text
从全池中逐步选择中心题
每次选择距离已有中心最远的题
直到选够 count
```

增量：

```text
计算新增题到已有中心的距离
如果新增题形成新的远距离区域，则加入候选中心集合
更新旧题和新增题的最近中心及覆盖半径
必要时替换部分旧中心
最终从当前全池得到新的中心集合
```

需要保存：

```text
selected_center_question_ids
nearest_center_by_question
distance_to_nearest_center
cover_radius
embedding_model_code
```

### 5.4 Facility Location

全量：

```text
构建候选题之间的相似度或近邻关系
贪心选择边际覆盖收益最大的题
直到选够 count
```

增量：

```text
只计算新增题与已有题/已有代表题之间的相似度
更新每道题当前被代表的最大相似度
重新评估新增题和受影响旧题的边际收益
允许局部替换旧代表题
最终从当前全池得到新的代表集合
```

需要保存：

```text
selected_question_ids
current_best_similarity_by_question
covered_by_question
candidate_gain_cache
nearest_neighbor_index 或近邻缓存
embedding_model_code
```

### 5.5 Graph Cut

全量：

```text
构建当前全池的近邻图
基于图割目标选择代表性强且冗余低的题
```

增量：

```text
为新增题建立近邻边
将新增节点接入旧图
更新受影响局部子图的边权和收益
在局部候选集合上执行替换/补选
最终从当前全池得到新的选中集合
```

需要保存：

```text
neighbor_graph
edge_weights
selected_node_ids
node_gain_cache
diversity_penalty_cache
embedding_model_code
```

### 5.6 Uncertainty

Uncertainty 依赖模型预测，不完全属于传统 CoreSet，但可以纳入主动学习选题策略。

如果模型没有变化：

```text
复用旧题 uncertainty 分数
只对新增题做 inference
合并后从当前全池取最高不确定性的 count 道
```

如果模型重新训练：

```text
理论上需要对当前全池重新 inference
```

可优化为：

```text
优先重算新增题
重算旧题中靠近选题边界的一部分
逐步刷新缓存
```

需要保存：

```text
model_version_id
prediction_scores
confidence / entropy / margin
prediction_timestamp
```

### 5.7 MoE 融合策略

MoE 应被视为多个子策略的组合。

增量方式：

```text
每个子策略维护自己的增量状态
新增题加入后分别更新各子策略分数
按融合权重合成最终分数
从当前全池选择 count 道
```

需要保存：

```text
sub_strategy_states
per_question_sub_scores
fusion_weights
final_score_cache
selected_question_ids
```

## 6. 数据结构建议

建议引入算法状态表，而不是只依赖 recommendation_batches 和 model_coreset_runs。

### 6.1 coreset_algorithm_states

建议字段：

```text
id
run_id
batch_id
strategy
data_scope
embedding_model_code
embedding_model_id
requested_count
candidate_count
selected_count
snapshot_created_before
state_version
state_json
artifact_path
created_at
```

说明：

```text
state_json 存轻量元数据
artifact_path 存较大的算法状态文件，如聚类中心、簇分配、近邻图
```

### 6.2 状态文件建议

对 K-Means，可保存：

```json
{
  "strategy": "kmeans",
  "embedding_model_code": "math-roberta-mlm-v1",
  "cluster_count": 400,
  "cluster_centers_path": "...",
  "assignments_path": "...",
  "representatives": [
    {
      "cluster_id": 0,
      "question_id": 123,
      "distance_to_center": 0.031
    }
  ]
}
```

对于 Facility Location / Graph Cut，不建议把完整相似度矩阵写入数据库 JSON，应使用文件或专门索引存储。

## 7. 前端交互调整

### 7.1 文案调整

当前按钮：

```text
增量更新新导入题
```

建议改为：

```text
增量更新当前题池
```

当前基线说明建议从：

```text
待增量更新题数 0，历史锚点 400，快照截止 ...
```

改为：

```text
当前未标注池 49600，较基线新增 10000，历史结构 400，快照截止 ...
```

### 7.2 算法切换提示

当用户切换算法时，前端应重新查询当前算法的可用基线。

如果没有匹配基线：

```text
当前算法暂无增量基线，请先运行一次全量选题。
```

此时禁用增量按钮。

如果有匹配基线：

```text
当前增量基线：rec_xxx
算法：K-Means
当前未标注池：49600
较基线新增：10000
```

### 7.3 结果展示

结果不应表达为“从新增题中选出”。

建议展示：

```text
当前候选池 49600
较基线新增 10000
本次选中 400
已加入待标注池 400
复用基线：rec_xxx
```

## 8. 后端流程建议

### 8.1 启动全量任务

```text
1. 查询当前全部未标注候选题
2. 确认候选题 embedding 完整
3. 根据 strategy 执行全量选择
4. 写入 RecommendationBatch / RecommendationItem
5. 保存 ModelCoresetRun
6. 保存 coreset_algorithm_states
```

### 8.2 启动增量任务

```text
1. 根据 strategy + data_scope + embedding_model_code 查找最近可用基线
2. 如果无基线，拒绝增量运行并提示先跑全量
3. 查询当前全部未标注候选题
4. 查询较基线新增的未标注题
5. 读取算法状态
6. 执行对应 strategy 的增量状态更新
7. 从当前全部候选题中输出 count 道
8. 写入 RecommendationBatch / RecommendationItem
9. 保存新的 ModelCoresetRun 和算法状态
```

## 9. 与 embedding 的关系

系统当前已经在导入流程中尝试为新题自动生成 embedding。

增量更新依赖这个前提：

```text
新导入题必须有当前 embedding 模型版本下的向量
```

如果存在缺失：

```text
应先触发缺失 embedding 补齐
补齐失败时，应在 CoreSet 任务中明确提示缺失数量
```

不建议在 CoreSet 主任务中静默忽略大量缺失 embedding，否则候选池规模会被低估。

## 10. 分阶段落地方案

### 第一阶段：修正语义和 UI

目标：

```text
避免继续表达“只从新增题中选题”
```

改动：

```text
前端按钮和提示文案调整
增量基线按 strategy 隔离
增量任务结果展示当前全池规模和新增规模
```

### 第二阶段：修正候选池范围

目标：

```text
增量任务最终从当前全部未标注题中选题
```

改动：

```text
不再仅使用 created_after 加载新增候选作为最终候选池
新增题只作为状态更新输入
全池候选作为最终选择范围
```

### 第三阶段：先实现 K-Means 真增量

目标：

```text
复用 K-Means 聚类状态，支持新增题并入旧簇和局部重选代表题
```

原因：

```text
当前系统主要使用 K-Means 覆盖
K-Means 状态结构相对清晰，最适合先落地
```

### 第四阶段：扩展 Facility Location / Graph Cut

目标：

```text
引入近邻缓存、覆盖收益缓存和局部图更新
```

这部分复杂度较高，应在 K-Means 稳定后推进。

### 第五阶段：MoE 统一状态管理

目标：

```text
为融合策略建立子策略状态管理与分数缓存机制
```

## 11. 验收标准

功能语义验收：

```text
导入新题后，增量 CoreSet 的最终候选池是当前全部未标注题
切换算法后，如果该算法没有基线，不能执行增量更新
同算法增量能显示正确的当前池规模、新增规模和复用基线
```

结果数据验收：

```text
RecommendationBatch.context_json 记录 source_run_no、baseline_run_no、strategy、embedding_model_code
ModelCoresetRun.metrics_json 记录 current_pool_count、new_unlabeled_count、baseline_state_id
算法状态可被后续同算法增量任务读取
```

质量验收：

```text
增量更新输出的 count 道题来自当前全池，而不是只来自新增题
新题大量进入某个知识/语义区域时，选题分布能反映当前全池分布变化
已进入待标注或标注中的题不会再次进入本次候选池
```

## 12. 当前结论

V8 的 CoreSet 增量更新应定义为：

```text
基于同算法历史状态，对新未标注数据加入后的当前未标注全池进行局部状态更新，
并从更新后的全池中重新选择 count 道代表题。
```

这能同时满足：

```text
主动学习继续从未标注池中选题
新导入数据影响整体分布
避免每轮都完全重算 4 万到 5 万题的 CoreSet 结构
不同算法的增量状态互不混用
```
