// 自动刷新数据
function refreshData() {
    fetch('/api/latest')
        .then(response => response.json())
        .then(data => {
            console.log('Latest data:', data);
        })
        .catch(error => console.error('Error:', error));
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
    console.log('Stock Analysis System Loaded');

    // 每5分钟刷新一次数据
    // setInterval(refreshData, 5 * 60 * 1000);
});

// 股票分析功能
function analyzeStock() {
    const code = document.getElementById('stockCode').value.trim();

    // 验证股票代码
    if (!code) {
        alert('请输入股票代码');
        return;
    }

    if (!/^\d{6}$/.test(code)) {
        alert('请输入6位数字股票代码');
        return;
    }

    // 显示加载状态
    const resultDiv = document.getElementById('analysisResult');
    const contentDiv = document.getElementById('resultContent');

    resultDiv.style.display = 'flex';
    contentDiv.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>正在获取${code}的数据并进行AI分析...</p>
        </div>
    `;

    // 调用API
    fetch(`/api/analyze/${code}`)
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                displayAnalysisResult(result.data);
            } else {
                contentDiv.innerHTML = `
                    <div class="error-message">
                        <h4>❌ 分析失败</h4>
                        <p>${result.error}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            contentDiv.innerHTML = `
                <div class="error-message">
                    <h4>❌ 请求失败</h4>
                    <p>${error.message}</p>
                </div>
            `;
        });
}

// 显示分析结果
function displayAnalysisResult(data) {
    const contentDiv = document.getElementById('resultContent');
    const titleDiv = document.getElementById('resultTitle');

    titleDiv.textContent = `${data.name} (${data.code})`;

    const changeClass = data.change_pct >= 0 ? 'positive' : 'negative';
    const changeSymbol = data.change_pct >= 0 ? '📈' : '📉';

    contentDiv.innerHTML = `
        <h4>${changeSymbol} 今日行情</h4>
        <table class="data-table">
            <tr>
                <th>昨收</th>
                <td>¥${data.yesterday_close.toFixed(2)}</td>
            </tr>
            <tr>
                <th>今开</th>
                <td>¥${data.today_open.toFixed(2)}</td>
            </tr>
            <tr>
                <th>最高/最低</th>
                <td>¥${data.today_high.toFixed(2)} / ¥${data.today_low.toFixed(2)}</td>
            </tr>
            <tr>
                <th>今收</th>
                <td class="${changeClass}">¥${data.today_close.toFixed(2)}</td>
            </tr>
            <tr>
                <th>涨跌幅</th>
                <td class="${changeClass}"><strong>${data.change_pct >= 0 ? '+' : ''}${data.change_pct.toFixed(2)}%</strong></td>
            </tr>
            <tr>
                <th>振幅</th>
                <td>${data.amplitude.toFixed(2)}%</td>
            </tr>
            <tr>
                <th>收盘位置</th>
                <td>${data.close_position.toFixed(1)}%</td>
            </tr>
            <tr>
                <th>量比</th>
                <td>${data.volume_ratio.toFixed(2)}x</td>
            </tr>
        </table>
        
        <h4>📊 技术指标</h4>
        <table class="data-table">
            <tr>
                <th>MA5</th>
                <td>¥${data.ma5.toFixed(2)} ${data.today_close > data.ma5 ? '✅' : '❌'}</td>
            </tr>
            <tr>
                <th>MA10</th>
                <td>¥${data.ma10.toFixed(2)} ${data.today_close > data.ma10 ? '✅' : '❌'}</td>
            </tr>
            <tr>
                <th>MA20</th>
                <td>¥${data.ma20.toFixed(2)} ${data.today_close > data.ma20 ? '✅' : '❌'}</td>
            </tr>
            <tr>
                <th>均线排列</th>
                <td>${data.ma5 > data.ma10 && data.ma10 > data.ma20 ? '✅ 多头排列' : '❌ 非多头'}</td>
            </tr>
        </table>
        
        <div class="ai-analysis-box">
            <h4>🤖 AI深度分析</h4>
            <p>${data.ai_analysis}</p>
        </div>
    `;
}

// 关闭结果窗口
function closeResult() {
    document.getElementById('analysisResult').style.display = 'none';
}

// 点击背景关闭
document.addEventListener('click', function (e) {
    const resultDiv = document.getElementById('analysisResult');
    if (resultDiv && e.target === resultDiv) {
        closeResult();
    }
});

// 支持回车键搜索
document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('stockCode');
    if (input) {
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                analyzeStock();
            }
        });
    }
});

// 自动刷新数据
function refreshData() {
    fetch('/api/latest')
        .then(response => response.json())
        .then(data => {
            console.log('Latest data:', data);
        })
        .catch(error => console.error('Error:', error));
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
    console.log('Stock Analysis System Loaded');

    // 每5分钟刷新一次数据
    // setInterval(refreshData, 5 * 60 * 1000);
});
