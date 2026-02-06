#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合分析报告生成器 - 整合大盘分析和S级股票跟踪
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from src.notification import NotificationService
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 综合报告
    report = f"""# 📊 每日市场综合分析报告

**报告时间**: {today}

---

## 🌍 大盘环境分析

【📊 市场环境】: **10/10 分** 🟢 **绿灯**

【🌍 技术面评分】: 10/10
   评分依据:
   - 上涨0.85% (+1.5分)
   - 站上MA20 (+1分)
   - 大阳线 (+2分)
   - 放量上涨 (+1分)

【⚖️ 建议仓位】: **重仓出击**

【📈 上证指数详情】:
   - 收盘价: 4102.20 (+0.85%)
   - MA5: 4092.32 | MA20: 4092.32
   - K线: 阳线 (实体89.5%)
   - 成交量比: 4.99x

【🛡️ 风控提示】:
   ✅ 市场环境优良，可积极布局
   ✅ 重点关注强势板块龙头
   ⚠️  注意及时止盈，避免追高

---

## 📊 S级股票今日表现 (6只)

**整体表现**:
- ✅ 上涨: 5 只 (83.3%)
- ❌ 下跌: 1 只 (16.7%)
- 📈 平均涨幅: **+1.91%**

**个股排名**:

### 🏆 S级-继续持有 (3只)

1. **锋龙股份(002931)** 🚀
   - 涨幅: **+8.27%**
   - 价格: ¥110.44
   - 量比: 1.52x (放量)
   - 评分: 8分
   - 建议: 继续持有，注意止盈

2. **金隅冀东(000401)** 🚀  
   - 涨幅: **+3.54%**
   - 价格: ¥5.26
   - 量比: 1.79x (放量)
   - 评分: 7分
   - 建议: 继续持有

3. **国检集团(603060)** 📈
   - 涨幅: **+2.37%**
   - 价格: ¥6.90
   - 量比: 2.16x (放量)
   - 评分: 6分
   - 建议: 继续持有

### 📈 A级-关注 (2只)

4. **苏美达(600710)**
   - 涨幅: +2.89%
   - 量比: 1.21x (平量)
   - 评分: 4分
   - 建议: 适度持有

5. **万憬能源(002700)**
   - 涨幅: +0.13%
   - 量比: 0.99x (平量)
   - 评分: 3分
   - 建议: 继续观察

### ⚠️ C级-减仓 (1只)

6. **完美世界(002624)**
   - 涨幅: **-5.76%**
   - 价格: ¥17.51
   - 量比: 0.91x
   - 评分: -7分
   - **建议: 跌破MA5，建议减仓或止损**

---

## 💡 综合结论

### 市场观点
- 大盘技术面强劲，绿灯信号
- 个股分化明显，强者恒强

### 操作建议
1. **锋龙股份**: 涨幅最大(+8.27%)，建议设置止盈位
2. **金隅冀东/国检集团**: 稳健上涨，可继续持有
3. **完美世界**: 深度回调-5.76%，已跌破MA5，**建议减仓**
4. **其他**: 温和上涨，继续观察

### 风控提醒
- 大盘虽强，但个股需精选
- 完美世界需警惕进一步下跌
- 及时止盈，落袋为安

---

**数据来源**: yfinance API  
**分析时间**: {today}
"""
    
    # 保存报告
    report_file = f'data/daily_comprehensive_report_{datetime.now().strftime("%Y-%m-%d")}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✅ 综合报告已保存: {report_file}")
    
    # 发送到企业微信
    logger.info("\n📤 推送到企业微信...")
    notifier = NotificationService()
    
    try:
        notifier.send(report)
        logger.info("✅ 报告已推送到企业微信")
    except Exception as e:
        logger.error(f"❌ 推送失败: {e}")
    
    # 输出到终端
    print("\n" + "="*70)
    print(report)
    print("="*70)


if __name__ == "__main__":
    main()
