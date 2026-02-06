# 🔑 Railway环境变量配置指南

## 🚨 **重要：必须配置才能使用AI功能**

Railway部署成功了，但AI分析功能需要配置API Key才能工作。

---

## 📋 **配置步骤**

### 1. 打开Railway项目设置

1. 访问 https://railway.app/
2. 登录后进入你的项目
3. 点击 "Variables" 标签

### 2. 添加环境变量

添加以下2个环境变量（必须完全一样）：

#### **变量1：OPENAI_API_KEY**
```
名称：OPENAI_API_KEY
值：你的DeepSeek API Key（以sk-开头的字符串）
```

#### **变量2：OPENAI_BASE_URL**
```
名称：OPENAI_BASE_URL
值：https://api.deepseek.com/v1
```

### 3. 保存并重新部署

1. 点击 "Add" 保存每个变量
2. Railway会自动重新部署
3. 等待2-3分钟

---

## 🔍 **如何获取DeepSeek API Key**

如果你还没有DeepSeek API Key：

1. 访问：https://platform.deepseek.com/
2. 注册/登录账号
3. 进入"API Keys"页面
4. 创建新的API Key
5. 复制Key（以`sk-`开头）
6. 粘贴到Railway的环境变量中

---

## ✅ **验证配置**

配置完成后，访问你的Railway网址：
https://web-production-d20e7.up.railway.app/

测试步骤：
1. 在搜索框输入：`600519`
2. 点击"🔍 AI分析"
3. 应该能看到完整的AI分析结果

---

## ❓ **常见问题**

### Q1: 配置后还是失败？
- 确认API Key是否正确（以`sk-`开头）
- 确认BASE_URL是否准确：`https://api.deepseek.com/v1`
- 等待Railway重新部署完成（2-3分钟）

### Q2: 如果没有DeepSeek API？
可以用其他兼容OpenAI的API：
- OpenAI官方API
- 其他国内API服务

只需修改 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`

### Q3: 不想配置AI功能？
不配置也能用，只是：
- ✅ 股票数据照常显示
- ❌ AI分析会显示"AI分析未配置"

---

## 🎯 **配置示例**

**在Railway Variables页面添加**：

| 变量名 | 值 |
|--------|-----|
| OPENAI_API_KEY | sk-xxxxxxxxxxxxxxxxxxxxxxxx |
| OPENAI_BASE_URL | https://api.deepseek.com/v1 |

点击"Add" → Railway自动重新部署 → 完成！

---

## 📞 **需要帮助？**

如果遇到问题：
1. 检查Railway部署日志
2. 确认环境变量是否保存成功
3. 测试API Key是否有效

配置完成后，你的股票分析系统就能完整运行了！🚀
