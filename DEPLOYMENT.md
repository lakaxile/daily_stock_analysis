# 股票分析Web应用部署指南

## 📦 本地运行

### 1. 安装依赖
```bash
cd /Users/gzy013/daily_stock_analysis/daily_stock_analysis
pip install -r requirements_web.txt
```

### 2. 启动应用
```bash
python web_app.py
```

访问: http://localhost:5000

---

## 🌐 外网访问方案

### 方案1: Railway (推荐 - 最简单)

**优点**: 免费、自动部署、支持Python、提供域名
**缺点**: 每月500小时免费额度

#### 步骤:
1. 访问 https://railway.app/
2. 用GitHub账号登录
3. 创建新项目 → 选择"Deploy from GitHub repo"
4. 连接你的仓库
5. 设置启动命令: `gunicorn web_app:app`
6. 自动分配域名，即可访问！

### 方案2: Vercel (推荐 - 速度快)

**优点**: CDN加速、免费、自动部署
**缺点**: 需要改造成Serverless架构

#### 步骤:
1. 访问 https://vercel.com/
2. 导入GitHub仓库
3. 框架选择"Other"
4. 设置构建命令和启动命令
5. 部署完成后获得域名

### 方案3: Render (稳定可靠)

**优点**: 免费tier、简单易用
**缺点**: 冷启动时间较长

#### 步骤:
1. 访问 https://render.com/
2. 创建Web Service
3. 连接GitHub仓库
4. 选择环境: Python 3
5. 启动命令: `gunicorn web_app:app --bind 0.0.0.0:$PORT`
6. 自动部署并分配域名

### 方案4: PythonAnywhere (专为Python优化)

**优点**: 专业Python托管、配置简单
**缺点**: 免费版有一些限制

#### 步骤:
1. 访问 https://www.pythonanywhere.com/
2. 注册免费账户
3. 打开Bash console上传代码
4. 在Web标签创建新应用
5. 配置WSGI文件指向web_app.py

### 方案5: Cloudflare Pages + Workers (高级)

**优点**: 全球CDN、完全免费
**缺点**: 需要改造成静态页面+API

---

## 🚀 快速部署步骤 (Railway)

### 1. 准备GitHub仓库
```bash
cd /Users/gzy013/daily_stock_analysis/daily_stock_analysis
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. 创建Procfile
```
web: gunicorn web_app:app
```

### 3. 创建runtime.txt
```
python-3.11
```

### 4. 部署到Railway
- 访问 https://railway.app/new
- 选择"Deploy from GitHub repo"
- 连接仓库并部署
- 等待构建完成
- 点击生成的域名访问

---

## 🔒 安全设置

### 修改 web_app.py 中的密钥:
```python
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 改为随机字符串
```

### 添加认证 (可选):
```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    if username == "admin" and password == "your-password":
        return username
    
@app.route('/')
@auth.login_required
def index():
    ...
```

---

## 📱 移动端访问

所有部署方案都支持移动端访问，响应式设计已内置。

---

## 🔄 自动更新

### 设置定时任务更新数据:
```bash
# crontab -e
0 15 * * 1-5 cd /path/to/project && python scripts/strategy_scanner.py
30 15 * * 1-5 cd /path/to/project && python scripts/scan_and_analyze.py
```

---

## 💡 推荐方案

**最简单**: Railway → 5分钟部署完成
**最稳定**: Render → 适合长期运行
**最快速**: Vercel → 全球CDN加速

选择Railway开始吧！
