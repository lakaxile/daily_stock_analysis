# 🔧 Railway部署修复指南

## 📊 当前问题

你的Railway项目有**2个服务**，但配置混乱：

1. **`web` 服务** - 构建失败 ❌
   - 错误: `secret OPENAI_BASE_URL: not found`
   - 域名: https://web-production-d20e7.up.railway.app/ (无法访问)

2. **`daily_stock_analysis` 服务** - 在线但配置不完整 ⚠️
   - API Keys还是占位符

---

## ✅ **修复步骤**

### **方案A: 删除`web`服务，只保留一个（推荐）**

#### **Step 1: 删除失败的`web`服务**

1. 在Railway Dashboard，进入你的项目 "striking-wholeness"
2. 找到 **`web`** 服务（显示红色"FAILED"）
3. 点击该服务
4. 点击右上角 **"Settings"**
5. 滚动到底部，点击 **"Delete Service"**
6. 确认删除

#### **Step 2: 配置`daily_stock_analysis`服务**

1. 点击 **`daily_stock_analysis`** 服务
2. 进入 **"Variables"** 标签
3. **修改以下变量**：

   **必须修改的**：
   ```
   GEMINI_API_KEY = (填入你的真实Gemini API Key)
   WEBUI_ENABLED = true
   ```

   **可选添加（如果你想用OpenAI/DeepSeek）**：
   ```
   OPENAI_API_KEY = (你的API Key)
   OPENAI_BASE_URL = https://api.deepseek.com/v1
   ```

4. 点击每个变量右侧的 **"Save"** 按钮

#### **Step 3: 生成公网域名**

1. 在 `daily_stock_analysis` 服务中
2. 点击 **"Settings"** 标签
3. 找到 **"Networking"** 部分
4. 点击 **"Generate Domain"**
5. Railway会分配一个新域名（如：`daily-stock-analysis-production.up.railway.app`）

#### **Step 4: 等待重新部署**

- Railway会自动重新部署
- 等待2-3分钟
- 看到绿色 ✓ 表示成功

---

### **方案B: 修复`web`服务（如果你想保留它）**

#### **Step 1: 添加环境变量到`web`服务**

1. 点击 **`web`** 服务
2. 进入 **"Variables"** 标签
3. 添加这些变量：
   ```
   GEMINI_API_KEY = (你的Gemini API Key)
   OPENAI_BASE_URL = https://api.deepseek.com/v1
   OPENAI_API_KEY = (你的OpenAI/DeepSeek API Key，可选)
   ```

#### **Step 2: 触发重新部署**

1. 在 **"Deployments"** 标签
2. 点击 **"Redeploy"** 按钮

---

## 🔑 **如何获取API Key**

### **Gemini API Key**（推荐，免费额度大）

1. 访问：https://makersuite.google.com/app/apikey
2. 创建API Key
3. 复制Key

### **DeepSeek API Key**（便宜，性能好）

1. 访问：https://platform.deepseek.com/
2. 注册/登录
3. 创建API Key
4. 复制Key（以`sk-`开头）

---

## ✅ **修复完成后的测试**

1. 访问你的新域名（在Railway Networking中可见）
2. 在搜索框输入：`600519`
3. 点击"🔍 AI分析"
4. 应该能看到完整的AI分析结果

---

## 💡 **推荐配置**

**最简单的配置**（仅需1个API Key）：
```
GEMINI_API_KEY = (你的Gemini Key)
WEBUI_ENABLED = true
```

这样就能使用Google Gemini进行AI分析了！

---

现在去Railway按照 **方案A** 操作吧！删除失败的`web`服务，配置好`daily_stock_analysis`服务即可！
