# README — GoldFish-Stock 个股舆情分析引擎

## 定位

**不预测股价，只分析资金分歧。**

恒指权重低的个股（B站、TME、PDD等）无法用恒指沙盘分析。
本项目用LLM多Agent对话，定性判断各类资金对个股事件的解读差异。

## 与 GoldFish-B 的区别

| | GoldFish-B | GoldFish-Stock |
|---|---|---|
| 分析对象 | 恒指整体 | 个股 |
| 输出 | 指数点位变化 | 定性分歧判断 |
| 适合 | 腾讯/阿里等权重股、宏观事件 | B站/TME/PDD等中小权重股 |

## 5个分析师Agent

| Agent | 风格 | 关注点 |
|-------|------|--------|
| 量化对冲 | Two Sigma/Citadel | 数字偏差、估值倍数 |
| 成长外资 | Baillie Gifford | 长期赛道、用户增长 |
| 港股价值派 | 惠理基金 | 估值、现金流、回购 |
| 南向散户 | 内地游资 | 政策、热点、技术面 |
| 风险套利 | 事件驱动 | 财报后3-10日动能 |

## 使用方法

```bash
# 安装依赖
pip install openai pyyaml

# 分析B站Q4财报
python3 stock_analyst.py events/bilibili_q4.yaml

# 分析自定义事件（新建yaml放入events/目录）
python3 stock_analyst.py events/your_event.yaml
```

## 事件文件格式

```yaml
events:
  - stock: "公司名 (股票代码)"
    event_type: "财报/政策/并购/..."
    description: |
      事件描述（自由文本）
    key_metrics:
      营收: "xxx亿（+xx% YoY）"
      利润: "..."
    context: |
      背景信息、当前股价、竞争格局等
```

## 已有场景

- `events/bilibili_q4.yaml` — B站 Q4/FY2025财报（真实数据）
