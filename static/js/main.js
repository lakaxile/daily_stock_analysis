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
