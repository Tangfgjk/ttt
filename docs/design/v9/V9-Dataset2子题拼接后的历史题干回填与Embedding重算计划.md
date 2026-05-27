# V9-Dataset2 子题拼接后的历史题干回填与 Embedding 重算计划

## 1. 背景

本轮已经修复 `dataset2_question_json` 导入链路中只提取主题干 `question`、遗漏 `subQues` 子题的问题。

当前已完成的修复包括：

- 新导入的 Dataset2 题目会将 `question + subQues` 拼接后作为完整题干入库
- 管理员、复核员、标注员相关页面在读取历史题目时，会从原始 JSON 中补齐 `subQues`，保证界面上可以看到完整题干

也就是说，题目展示问题已经解决。

## 2. 暂未处理的问题

历史题目虽然在读取时能展示完整题干，但数据库底层仍可能存在以下不一致：

1. `question_contents.stem_text / stem_html` 仍然保存的是旧的、不含子题的题干
2. `question_dedup_features` 仍然基于旧题干生成
3. `question_embeddings` 仍然基于旧题干生成

因此，当前系统里会出现“界面显示是完整题干，但去重特征和向量仍对应旧短题干”的情况。

## 3. 为什么要单独放到 V9 处理

这次优先目标是修复题目展示与标注可读性问题，避免影响管理员、复核员、标注员日常使用。

如果在同一轮里直接叠加历史回填、去重特征重算、embedding 重算，会额外带来：

- 批量更新历史题目的数据风险
- 去重候选与内容哈希变化带来的连锁影响
- embedding 重算耗时与资源占用
- 需要额外确认主动学习 / CoreSet / 可视化等链路的兼容性

所以这里先记录到 V9，后续单独评审并执行。

## 4. 影响范围

### 4.1 当前不受影响

- 题目详情页显示
- 标注员领取题目后的题干显示
- 复核员复核时的题干显示
- 管理员查看题目与导入详情时的题干显示

### 4.2 当前仍可能受影响

- 历史题目的 dedup 特征匹配结果
- 历史题目的 embedding 向量
- 依赖 embedding 的主动学习 / CoreSet 候选质量
- 依赖 embedding 的可视化分布结果

## 5. V9 建议处理方案

### 5.1 历史题干回填

针对 `dataset2_question_json` 来源的历史题目：

- 读取 `source_question_records.raw_payload`
- 按 `question + subQues(sortIndex 顺序)` 重建完整题干
- 回填 `question_contents.stem_text`
- 如有需要，同时更新 `question_contents.stem_html`

### 5.2 去重特征重算

对已回填题干的题目重新执行：

- `question_dedup_service.sync_question_feature(question)`

确保内容哈希、标准化题干、去重特征与最新题干一致。

### 5.3 Embedding 重算

对同一批题目重新生成 embedding，而不是只补缺失值。

注意：

- 当前 `/visualization/embeddings/rebuild` 只会补“缺失 embedding”
- 不能覆盖“已有但基于旧题干生成的 embedding”

因此 V9 需要新增“强制重算指定题目 embedding”的能力，或提供一次性离线脚本。

## 6. 实施建议

建议按以下顺序推进：

1. 先做只读统计，确认受影响的 Dataset2 历史题数量
2. 先在测试环境执行历史题干回填
3. 校验题干回填后的去重特征变化
4. 对受影响题目批量重算 embedding
5. 抽样验证管理员 / 复核员 / 标注员页面、主动学习、可视化结果

## 7. 验收标准

- 历史 Dataset2 题目的数据库题干与页面展示一致
- dedup 特征与完整题干一致
- embedding 与完整题干一致
- 主动学习 / CoreSet / 可视化链路无明显回归

## 8. 当前结论

本事项已记录到 V9。

当前版本先保持：

- 展示层正常可用
- 新导入数据按完整题干处理
- 历史数据底层回填、dedup 重算、embedding 重算延后到 V9 单独处理
