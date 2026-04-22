# 项目结构导航

## 1. 目录/文件结构（当前）
```text
virtual_data_collection_rl_2/
├─ docs/
│  ├─ project_overview/
│  │  ├─ overview.md
│  │  ├─ file-map.md
│  │  └─ changelog.md
│  ├─ project_plan/
│  │  ├─ master-plan.md
│  │  └─ step-01-project-baseline.md
└─ （业务代码目录后续按步骤逐步落地）
```

## 2. 关键文件职责（每个文件 1 句话 + 何时需要修改）
- `docs/project_overview/overview.md`：项目全局说明与当前阶段摘要；当目标、边界、主流程、风险、当前步骤变化时更新。
- `docs/project_overview/file-map.md`：结构导航与符号索引；当目录结构、关键职责、符号设计变化时更新。
- `docs/project_overview/changelog.md`：记录代码/配置/脚本/依赖/运行方式变更；发生非文档工程变更时追加。
- `docs/project_plan/master-plan.md`：项目总计划与门禁规则；当总步骤、推进规则、当前步骤状态变化时更新。
- `docs/project_plan/step-01-project-baseline.md`：当前步骤计划文档；当步骤内动作、验收标准、阻塞信息变化时更新。
- 规则说明：`docs/project_detailed/` 将在首个真实功能代码落地后，按 `<feature-name>.md` 规范重新创建。

## 3. 计划步骤与目录映射（当前）
- Step 1（进行中）：聚焦 `docs/project_overview/*`、`docs/project_plan/*`。
- Step 2（未开始）：预计涉及 `sim/scenes/*`、`sim/robots/fr3/*`、`sim/objects/cube/*`。
- Step 3（未开始）：预计涉及 `sim/primitives/pick_place.py`、`scripts/run_pick_place.sh`。
- Step 4（未开始）：预计涉及 `data_pipeline/collector/*`、`data_pipeline/dataset/*`。
- Step 5（未开始）：预计涉及 `training/ppo/*`、`training/eval/*`。
- Step 6（未开始）：预计涉及 `deploy/franka_bridge/*`、`scripts/run_real_pickplace.sh`。

## 4. 核心符号索引（名称、作用、核心原理）
以下为当前阶段建议符号，待代码落地后改为真实实现索引：

- `build_scene(task_name, robot_cfg, object_cfg)`
  - 作用：创建任务场景与机器人配置。
  - 核心原理：根据任务配置加载对象模板并注入物理参数。

- `collect_episode(task_name, policy, collector_cfg)`
  - 作用：执行一次采样回合并输出时序数据。
  - 核心原理：策略驱动交互，采样器按固定频率记录状态与动作。

- `sync_multimodal_streams(streams, ts_tolerance_ms)`
  - 作用：对齐多模态数据时间轴。
  - 核心原理：以统一时间基准进行重采样、插值与异常帧剔除。

- `preprocess_dataset(input_dir, output_dir, norm_cfg, augment_cfg)`
  - 作用：清洗并构建训练数据集。
  - 核心原理：先过滤异常，再标准化与增强，最后完成数据划分。

- `train_ppo(train_cfg, dataset_meta)`
  - 作用：执行 PPO 训练并保存检查点。
  - 核心原理：策略网络与价值网络迭代优化，依据优势函数更新参数。

- `evaluate_policy(policy_ckpt, eval_tasks, metrics_cfg)`
  - 作用：评估模型并输出关键指标。
  - 核心原理：批量回放任务并统计成功率、精度与鲁棒性。

- `deploy_to_franka(policy_ckpt, bridge_cfg)`
  - 作用：将策略部署到 Franka 真机。
  - 核心原理：动作映射、约束限幅与控制通信桥接。
