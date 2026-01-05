from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.responses import HTMLResponse
from typing import Dict, List, Any, Optional
import json
import logging
import asyncio
from datetime import datetime, timedelta
import psutil
import platform
import os

from api_server.utils.redis_manager import RedisManager, get_redis_manager
from shared.config import Config
from shared.models import SystemStats

logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket连接断开，剩余连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@router.get("/dashboard", response_class=HTMLResponse)
async def get_monitor_dashboard():
    """监控仪表板页面"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>分布式爬虫监控系统</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                color: white;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .card {
                background: white;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
            }
            .card-title {
                font-size: 1.3rem;
                font-weight: 600;
                color: #333;
            }
            .card-icon {
                font-size: 1.5rem;
                color: #667eea;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }
            .stat-item {
                text-align: center;
                padding: 15px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 10px;
            }
            .stat-value {
                font-size: 2rem;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }
            .stat-label {
                font-size: 0.9rem;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .chart-container {
                height: 300px;
                margin-top: 10px;
            }
            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            .status-running { background: #d4edda; color: #155724; }
            .status-paused { background: #fff3cd; color: #856404; }
            .status-stopped { background: #f8d7da; color: #721c24; }
            .log-container {
                background: #1a1a1a;
                color: #00ff00;
                padding: 15px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                font-size: 0.9rem;
                height: 300px;
                overflow-y: auto;
                margin-top: 10px;
            }
            .log-entry {
                margin-bottom: 5px;
                padding: 3px 0;
                border-bottom: 1px solid #333;
            }
            .log-time { color: #aaa; }
            .log-level-info { color: #00ff00; }
            .log-level-warning { color: #ffff00; }
            .log-level-error { color: #ff0000; }
            .websocket-status {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 10px 20px;
                border-radius: 20px;
                font-weight: 600;
                color: white;
                z-index: 1000;
            }
            .ws-connected { background: #28a745; }
            .ws-disconnected { background: #dc3545; }
            .refresh-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1rem;
                transition: background 0.3s;
                margin: 10px 0;
            }
            .refresh-btn:hover { background: #5a67d8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 分布式爬虫监控系统</h1>
                <p>实时监控爬虫节点状态、任务进度和系统性能</p>
            </div>
            
            <div class="websocket-status ws-disconnected" id="wsStatus">
                🔴 WebSocket 未连接
            </div>
            
            <div class="dashboard-grid">
                <!-- 系统概览 -->
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">📊 系统概览</h2>
                        <span class="card-icon">⚙️</span>
                    </div>
                    <div class="stats-grid" id="systemOverview">
                        <div class="stat-item">
                            <div class="stat-value" id="nodeCount">0</div>
                            <div class="stat-label">爬虫节点</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="activeTasks">0</div>
                            <div class="stat-label">活跃任务</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="queueSize">0</div>
                            <div class="stat-label">队列大小</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="itemsProcessed">0</div>
                            <div class="stat-label">已处理新闻</div>
                        </div>
                    </div>
                </div>
                
                <!-- 爬虫节点状态 -->
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">🖥️ 爬虫节点</h2>
                        <span class="card-icon">🔌</span>
                    </div>
                    <div id="nodeList">
                        <p>正在加载节点信息...</p>
                    </div>
                </div>
                
                <!-- 任务统计 -->
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">📈 任务统计</h2>
                        <span class="card-icon">📊</span>
                    </div>
                    <div class="chart-container" id="taskChart"></div>
                </div>
                
                <!-- 系统资源 -->
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">💻 系统资源</h2>
                        <span class="card-icon">⚡</span>
                    </div>
                    <div class="chart-container" id="resourceChart"></div>
                </div>
                
                <!-- 实时日志 -->
                <div class="card" style="grid-column: span 2;">
                    <div class="card-header">
                        <h2 class="card-title">📝 实时日志</h2>
                        <span class="card-icon">📋</span>
                    </div>
                    <div class="log-container" id="logContainer">
                        <!-- 日志将通过WebSocket动态添加 -->
                    </div>
                </div>
            </div>
            
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新页面</button>
        </div>
        
        <script>
            let ws = null;
            let reconnectInterval = null;
            let taskChart = null;
            let resourceChart = null;
            
            // 初始化图表
            function initCharts() {
                // 任务统计图表
                taskChart = echarts.init(document.getElementById('taskChart'));
                taskChart.setOption({
                    title: { text: '任务状态分布', left: 'center' },
                    tooltip: { trigger: 'item' },
                    legend: { orient: 'vertical', left: 'left' },
                    series: [{
                        name: '任务状态',
                        type: 'pie',
                        radius: '50%',
                        data: [
                            { value: 0, name: '运行中' },
                            { value: 0, name: '已完成' },
                            { value: 0, name: '失败' },
                            { value: 0, name: '等待中' }
                        ],
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowOffsetX: 0,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                        }
                    }]
                });
                
                // 系统资源图表
                resourceChart = echarts.init(document.getElementById('resourceChart'));
                resourceChart.setOption({
                    title: { text: '系统资源使用率', left: 'center' },
                    tooltip: { trigger: 'axis' },
                    legend: { data: ['CPU', '内存', '队列'], top: '10%' },
                    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                    xAxis: { type: 'category', boundaryGap: false, data: [] },
                    yAxis: { type: 'value', max: 100 },
                    series: [
                        {
                            name: 'CPU',
                            type: 'line',
                            smooth: true,
                            data: []
                        },
                        {
                            name: '内存',
                            type: 'line',
                            smooth: true,
                            data: []
                        },
                        {
                            name: '队列',
                            type: 'line',
                            smooth: true,
                            data: []
                        }
                    ]
                });
            }
            
            // 连接WebSocket
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/api/monitor/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    console.log('WebSocket连接已建立');
                    document.getElementById('wsStatus').className = 'websocket-status ws-connected';
                    document.getElementById('wsStatus').innerHTML = '🟢 WebSocket 已连接';
                    
                    // 清除重连定时器
                    if (reconnectInterval) {
                        clearInterval(reconnectInterval);
                        reconnectInterval = null;
                    }
                };
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        handleWebSocketMessage(data);
                    } catch (error) {
                        console.error('解析WebSocket消息失败:', error);
                    }
                };
                
                ws.onclose = function() {
                    console.log('WebSocket连接已断开');
                    document.getElementById('wsStatus').className = 'websocket-status ws-disconnected';
                    document.getElementById('wsStatus').innerHTML = '🔴 WebSocket 未连接';
                    
                    // 尝试重新连接
                    if (!reconnectInterval) {
                        reconnectInterval = setInterval(connectWebSocket, 5000);
                    }
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket错误:', error);
                };
            }
            
            // 处理WebSocket消息
            function handleWebSocketMessage(data) {
                const { type, payload } = data;
                
                switch (type) {
                    case 'system_stats':
                        updateSystemOverview(payload);
                        break;
                    case 'node_status':
                        updateNodeList(payload);
                        break;
                    case 'task_stats':
                        updateTaskChart(payload);
                        break;
                    case 'resource_stats':
                        updateResourceChart(payload);
                        break;
                    case 'log_entry':
                        addLogEntry(payload);
                        break;
                    case 'alert':
                        showAlert(payload);
                        break;
                }
            }
            
            // 更新系统概览
            function updateSystemOverview(stats) {
                document.getElementById('nodeCount').textContent = stats.crawler_nodes || 0;
                document.getElementById('activeTasks').textContent = stats.active_spiders || 0;
                document.getElementById('queueSize').textContent = stats.queue_size || 0;
                document.getElementById('itemsProcessed').textContent = stats.items_processed || 0;
            }
            
            // 更新节点列表
            function updateNodeList(nodes) {
                const nodeList = document.getElementById('nodeList');
                if (!nodes || nodes.length === 0) {
                    nodeList.innerHTML = '<p>暂无活跃节点</p>';
                    return;
                }
                
                let html = '<div style="display: grid; gap: 10px;">';
                nodes.forEach(node => {
                    const statusClass = node.status === 'running' ? 'status-running' : 
                                      node.status === 'idle' ? 'status-paused' : 'status-stopped';
                    const statusText = node.status === 'running' ? '运行中' : 
                                      node.status === 'idle' ? '空闲' : '停止';
                    
                    html += `
                        <div style="background: #f8f9fa; padding: 10px; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>${node.id}</strong>
                                    <div style="font-size: 0.8rem; color: #666;">
                                        CPU: ${node.cpu_usage || 0}% | 内存: ${node.memory_usage || 0}%
                                    </div>
                                </div>
                                <span class="status-badge ${statusClass}">${statusText}</span>
                            </div>
                            <div style="font-size: 0.9rem; margin-top: 5px;">
                                <div>蜘蛛: ${node.spiders.join(', ') || '无'}</div>
                                <div>处理数: ${node.items_processed || 0}</div>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                nodeList.innerHTML = html;
            }
            
            // 更新任务图表
            function updateTaskChart(stats) {
                if (!taskChart) return;
                
                const option = taskChart.getOption();
                option.series[0].data = [
                    { value: stats.running || 0, name: '运行中' },
                    { value: stats.completed || 0, name: '已完成' },
                    { value: stats.failed || 0, name: '失败' },
                    { value: stats.pending || 0, name: '等待中' }
                ];
                taskChart.setOption(option);
            }
            
            // 更新资源图表
            function updateResourceChart(stats) {
                if (!resourceChart) return;
                
                const now = new Date();
                const timeLabel = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
                
                const option = resourceChart.getOption();
                
                // 更新X轴
                let xAxisData = option.xAxis[0].data;
                xAxisData.push(timeLabel);
                if (xAxisData.length > 20) {
                    xAxisData.shift();
                }
                option.xAxis[0].data = xAxisData;
                
                // 更新CPU数据
                let cpuData = option.series[0].data;
                cpuData.push(stats.cpu || 0);
                if (cpuData.length > 20) {
                    cpuData.shift();
                }
                option.series[0].data = cpuData;
                
                // 更新内存数据
                let memoryData = option.series[1].data;
                memoryData.push(stats.memory || 0);
                if (memoryData.length > 20) {
                    memoryData.shift();
                }
                option.series[1].data = memoryData;
                
                // 更新队列数据
                let queueData = option.series[2].data;
                queueData.push(stats.queue || 0);
                if (queueData.length > 20) {
                    queueData.shift();
                }
                option.series[2].data = queueData;
                
                resourceChart.setOption(option);
            }
            
            // 添加日志条目
            function addLogEntry(log) {
                const logContainer = document.getElementById('logContainer');
                const levelClass = 'log-level-' + (log.level || 'info');
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                logEntry.innerHTML = `
                    <span class="log-time">[${log.timestamp}]</span>
                    <span class="${levelClass}">[${log.level.toUpperCase()}]</span>
                    ${log.message}
                `;
                logContainer.appendChild(logEntry);
                
                // 自动滚动到底部
                logContainer.scrollTop = logContainer.scrollHeight;
                
                // 限制日志数量
                const entries = logContainer.getElementsByClassName('log-entry');
                if (entries.length > 100) {
                    entries[0].remove();
                }
            }
            
            // 显示警报
            function showAlert(alert) {
                console.warn('系统警报:', alert);
                // 这里可以添加更复杂的警报显示逻辑
            }
            
            // 页面加载完成后初始化
            window.onload = function() {
                initCharts();
                connectWebSocket();
                
                // 初始加载数据
                fetch('/api/monitor/stats')
                    .then(response => response.json())
                    .then(data => updateSystemOverview(data));
                
                fetch('/api/monitor/nodes')
                    .then(response => response.json())
                    .then(data => updateNodeList(data));
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取系统统计信息"""
    try:
        # 获取爬虫节点数量
        crawler_nodes = await redis_manager.get_crawler_node_count()
        
        # 获取活跃爬虫数量
        active_spiders = await redis_manager.get_active_spider_count()
        
        # 获取总队列大小
        queue_size = await redis_manager.get_total_queue_size()
        
        # 获取已处理项目数
        items_processed = await redis_manager.get_total_items_processed()
        
        # 获取失败项目数
        items_failed = await redis_manager.get_total_items_failed()
        
        # 计算处理速率（需要历史数据）
        processing_rate = await redis_manager.get_processing_rate()
        
        # 获取系统运行时间（这里简化处理）
        uptime = await redis_manager.get_system_uptime()
        
        return SystemStats(
            crawler_nodes=crawler_nodes,
            active_spiders=active_spiders,
            queue_size=queue_size,
            items_processed=items_processed,
            items_failed=items_failed,
            processing_rate=processing_rate,
            uptime=uptime,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")

@router.get("/nodes")
async def get_crawler_nodes(
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取爬虫节点信息"""
    try:
        nodes = await redis_manager.get_crawler_nodes()
        return nodes
    except Exception as e:
        logger.error(f"获取爬虫节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取爬虫节点失败: {str(e)}")

@router.get("/tasks/summary")
async def get_tasks_summary(
    hours: int = Query(24, description="时间范围(小时)", ge=1, le=168),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取任务摘要"""
    try:
        # 获取最近N小时的任务统计
        summary = await redis_manager.get_tasks_summary(hours)
        return summary
    except Exception as e:
        logger.error(f"获取任务摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务摘要失败: {str(e)}")

@router.get("/performance")
async def get_performance_metrics(
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取性能指标"""
    try:
        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # 获取Redis性能指标
        redis_info = await redis_manager.get_redis_info()
        
        # 获取网络连接数
        connections = len(psutil.net_connections())
        
        # 获取磁盘使用情况
        disk_usage = psutil.disk_usage('/')
        
        metrics = {
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_usage": disk_usage.percent,
                "disk_total": disk_usage.total,
                "disk_free": disk_usage.free,
                "network_connections": connections
            },
            "redis": redis_info,
            "timestamp": datetime.now().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")

@router.get("/alerts")
async def get_system_alerts(
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取系统警报"""
    try:
        alerts = await redis_manager.get_system_alerts(severity, limit)
        return alerts
    except Exception as e:
        logger.error(f"获取系统警报失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统警报失败: {str(e)}")

@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = Query(None, description="日志级别过滤"),
    source: Optional[str] = Query(None, description="来源过滤"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=10000),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取系统日志"""
    try:
        logs = await redis_manager.get_system_logs(level, source, limit)
        return logs
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")

@router.get("/history/{metric}")
async def get_metric_history(
    metric: str,
    period: str = Query("1h", description="时间周期", regex="^(1h|6h|24h|7d|30d)$"),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取指标历史数据"""
    try:
        valid_metrics = ["cpu_usage", "memory_usage", "queue_size", "items_processed", "active_nodes"]
        if metric not in valid_metrics:
            raise HTTPException(status_code=400, detail=f"无效的指标，可选值: {', '.join(valid_metrics)}")
        
        history = await redis_manager.get_metric_history(metric, period)
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指标历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取指标历史数据失败: {str(e)}")

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """WebSocket端点，用于实时监控"""
    await manager.connect(websocket)
    
    # 定义后台更新任务
    async def send_updates():
        try:
            while True:
                try:
                    # 直接使用传入的 redis_manager 实例获取数据
                    # 这样更高效，避免了函数调用和重复的依赖注入
                    
                    # 1. 获取系统统计
                    stats = await redis_manager.get_system_stats() # 假设 RedisManager 有这个聚合方法
                    await websocket.send_json({"type": "system_stats", "payload": stats})
                    
                    # 2. 获取节点状态
                    nodes = await redis_manager.get_crawler_nodes()
                    await websocket.send_json({"type": "node_status", "payload": nodes})
                    
                    # 3. 获取任务统计
                    task_summary = await redis_manager.get_tasks_summary()
                    await websocket.send_json({"type": "task_stats", "payload": task_summary})
                    
                    # 4. 获取性能指标
                    # 注意：psutil 是阻塞的，在异步代码中调用需要小心
                    # 可以考虑使用 run_in_executor 来避免阻塞事件循环
                    loop = asyncio.get_running_loop()
                    cpu_percent = await loop.run_in_executor(None, psutil.cpu_percent, 0.1)
                    memory_percent = psutil.virtual_memory().percent
                    queue_size = await redis_manager.get_total_queue_size()
                    
                    resource_stats = {
                        "cpu": cpu_percent,
                        "memory": memory_percent,
                        "queue": queue_size
                    }
                    await websocket.send_json({"type": "resource_stats", "payload": resource_stats})
                    
                    # 5. 获取最新日志
                    logs = await redis_manager.get_system_logs(limit=5)
                    for log in logs:
                        await websocket.send_json({"type": "log_entry", "payload": log})

                    await asyncio.sleep(2) # 每2秒更新一次
                        
                except Exception as e:
                    logger.error(f"发送WebSocket更新失败: {e}")
                    # 即使发送失败，也继续循环，避免任务中断
                    await asyncio.sleep(5) # 失败后延迟更长时间再试
                        
        except asyncio.CancelledError:
            logger.info("WebSocket更新任务已被取消。")
            # 任务被取消时，正常退出
            pass

    # 创建并启动后台任务
    update_task = asyncio.create_task(send_updates())
    
    try:
        # 发送初始连接成功消息
        await websocket.send_json({
            "type": "connection_established",
            "message": "WebSocket连接已建立，开始接收实时数据...",
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持连接，等待客户端消息（即使我们不处理）
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info("WebSocket客户端已断开连接。")
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
    finally:
        # 无论连接是正常关闭还是异常中断，都确保后台任务被取消
        update_task.cancel()
        await update_task  # 等待任务完全结束
        manager.disconnect(websocket)
        logger.info(f"WebSocket连接已清理，当前连接数: {len(manager.active_connections)}")
@router.post("/alerts/test")
async def test_alert_system(
    message: str = "测试警报消息",
    severity: str = "info",
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """测试警报系统"""
    try:
        alert = {
            "id": f"test_{datetime.now().timestamp()}",
            "message": message,
            "severity": severity,
            "source": "api_test",
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False
        }
        
        # 保存警报
        await redis_manager.save_alert(alert)
        
        # 通过WebSocket广播警报
        await manager.broadcast(json.dumps({
            "type": "alert",
            "payload": alert
        }))
        
        return {
            "success": True,
            "message": "测试警报已发送",
            "alert": alert
        }
        
    except Exception as e:
        logger.error(f"测试警报系统失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试警报系统失败: {str(e)}")

@router.delete("/alerts/clear")
async def clear_alerts(
    days: int = Query(30, description="清理多少天前的警报", ge=1, le=365),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """清理旧警报"""
    try:
        cleared_count = await redis_manager.clear_old_alerts(days)
        
        return {
            "success": True,
            "message": f"已清理 {cleared_count} 个旧警报",
            "days": days
        }
        
    except Exception as e:
        logger.error(f"清理警报失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理警报失败: {str(e)}")