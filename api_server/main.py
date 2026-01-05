# api_server/main.py

import os
import time
from datetime import datetime
from fastapi import FastAPI, Request, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import uvicorn

# 导入你的路由和工具
from api_server.routes import crawler_routes
from api_server.routes import monitor_routes
from api_server.utils.redis_manager import redis_manager_instance, get_redis_manager

# ====================== 1. 初始化 FastAPI 应用 ======================
app = FastAPI(
    title="Power News Crawler API",
    description="A distributed news crawling system API",
    version="1.0.0",
)

# ====================== 2. Prometheus 指标和中间件 ======================
REQUEST_COUNTER = Counter(
    'api_requests_total', 'Total number of API requests', ['endpoint', 'method', 'status_code'], registry=REGISTRY
)
REQUEST_DURATION = Histogram(
    'api_request_duration_seconds', 'API request duration in seconds', ['endpoint', 'method'], registry=REGISTRY
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNTER.labels(
        endpoint=request.url.path,
        method=request.method,
        status_code=str(response.status_code)
    ).inc()
    REQUEST_DURATION.labels(endpoint=request.url.path, method=request.method).observe(duration)
    
    return response

@app.get("/metrics", include_in_schema=False)
async def metrics():
    return PlainTextResponse(generate_latest(REGISTRY), media_type="text/plain")

# ====================== 3. 应用生命周期事件 (关键) ======================
@app.on_event("startup")
async def startup_event():
    print("🚀 Application startup event triggered.")
    try:
        # 初始化 Redis 连接
        await redis_manager_instance.initialize()
    except Exception as e:
        print(f"💥 Failed to initialize services during startup: {e}")
        raise  # 初始化失败则停止应用

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Application shutdown event triggered.")
    # 关闭 Redis 连接
    await redis_manager_instance.close()

# ====================== 4. 核心接口定义 ======================
@app.get("/health")
async def health_check(redis_mgr = Depends(get_redis_manager)):
    """健康检查接口"""
    try:
        # 检查 Redis 连接
        await redis_mgr.client.ping()
        return JSONResponse(status_code=200, content={
            "status": "healthy", "service": "power-news-crawler-api",
            "timestamp": datetime.now().isoformat(), "redis": "connected"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()
        })

# ====================== 5. 注册你的路由 ======================
app.include_router(
    crawler_routes.router,
    prefix="/api/crawler",
    tags=["Crawler Management"]
)

app.include_router(
    monitor_routes.router,
    prefix="/api/monitor",
    tags=["Monitoring"]
)

# ====================== 6. 启动配置 ======================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        workers=int(os.getenv("UVICORN_WORKERS", 1)) # 生产环境建议 > 1
    )