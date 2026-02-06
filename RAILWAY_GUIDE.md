# 🚀 Railway 部署完整指南

## 📋 前提条件
- ✅ 代码已推送到GitHub
- ✅ 有GitHub账号

---

## 🎯 Railway部署步骤

### 第1步：访问Railway并登录

1. 打开浏览器，访问：https://railway.app/
2. 点击右上角 **"Login"**
3. 选择 **"Login with GitHub"**
4. 授权Railway访问你的GitHub账号

### 第2步：创建新项目

1. 登录后，点击 **"New Project"**
2. 选择 **"Deploy from GitHub repo"**
3. 如果是第一次使用，点击 **"Configure GitHub App"**
4. 选择你的仓库：`daily_stock_analysis`
5. 点击 **"Deploy Now"**

### 第3步：等待自动部署

Railway会自动：
- ✅ 检测到Python项目
- ✅ 读取 `Procfile` 配置
- ✅ 安装 `requirements_web.txt` 依赖
- ✅ 启动应用

部署过程大约需要 **2-3分钟**

### 第4步：生成公网域名

1. 部署成功后，点击你的项目
2. 进入 **"Settings"** 标签
3. 找到 **"Networking"** 部分
4. 点击 **"Generate Domain"**
5. 获得类似这样的域名：`your-app-production.railway.app`

### 第5步：访问你的网站！

打开生成的域名，就能看到你的股票分析系统了！

**示例域名**：
```
https://stock-analysis-production.railway.app
```

---

## 🔧 可选：环境变量配置

如果需要配置API Key（Railway部署时）：

1. 在Railway项目中，进入 **"Variables"** 标签
2. 添加环境变量：
   - `OPENAI_API_KEY` = 你的DeepSeek API Key
   - `OPENAI_BASE_URL` = `https://api.deepseek.com/v1`
   - `WECHAT_WEBHOOK` = 你的企业微信Webhook（可选）

3. 点击 **"Add"** 保存
4. Railway会自动重新部署

---

## 📱 自定义域名（可选）

如果你有自己的域名：

1. 在Railway项目 **"Settings"** 中
2. 找到 **"Custom Domain"**
3. 输入你的域名（如：`stock.yourdomain.com`）
4. 在你的域名DNS设置中添加CNAME记录：
   ```
   CNAME: stock → your-app.railway.app
   ```
5. 等待DNS生效（通常5-10分钟）

---

## 🔄 自动部署

Railway已配置自动部署：
- 每次推送代码到GitHub `main` 分支
- Railway自动检测并重新部署
- 无需手动操作！

---

## 💰 费用说明

**Railway免费额度**：
- ✅ 500小时/月免费运行时间
- ✅ 512MB内存
- ✅ 1GB磁盘空间
- ✅ 无限带宽

对于个人使用完全够用！

---

## ❓ 常见问题

### Q1: 部署失败怎么办？

查看 **"Deployments"** 标签的日志，常见问题：
- 依赖安装失败：检查 `requirements_web.txt`
- 启动命令错误：检查 `Procfile`
- 端口配置：Railway自动分配端口，无需修改

### Q2: 如何查看日志？

1. 点击项目
2. 进入 **"Deployments"** 标签
3. 点击最新的部署
4. 查看实时日志

### Q3: 数据怎么更新？

**方法1**：手动更新
- 在本地运行选股脚本
- 推送更新的 `data/` 文件到GitHub
- Railway自动重新部署

**方法2**：自动化（未来）
- 在Railway设置定时任务
- 自动运行选股脚本

---

## 🎉 完成！

恭喜！你的股票分析系统已经部署到公网，可以随时随地访问了！

**分享你的网站**：
- 复制Railway生成的域名
- 分享给朋友或在手机上访问
- 支持所有设备（响应式设计）

---

## 📞 需要帮助？

- Railway文档：https://docs.railway.app/
- Railway社区：https://discord.gg/railway
