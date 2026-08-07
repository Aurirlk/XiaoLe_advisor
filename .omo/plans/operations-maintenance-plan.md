# 小乐AI 运行和维护计划

> 版本: v1.0  
> 制定日期: 2026-06-24  
> 计划周期: 1个月（阶段性执行）  
> 优先级: 性能优化优先，故障应急预案并行

---

## TL;DR

> **目标**: 解决系统性能瓶颈（响应慢、并发不足、资源占用高），建立完善的故障应急体系
> **范围**: 性能优化 + 故障应急预案 + 日常运维流程
> **执行方式**: 人工执行，阶段性推进
> **监控工具**: ELK日志系统

---

## 一、现状分析

### 1.1 已识别的性能问题

| 问题 | 严重程度 | 影响范围 |
|------|----------|----------|
| 响应时间慢 | 🔴 高 | 用户体验 |
| 并发能力不足 | 🔴 高 | 系统可用性 |
| 数据库查询慢 | 🟡 中 | 查询效率 |
| 内存/CPU占用高 | 🟡 中 | 服务器资源 |

### 1.2 需要覆盖的故障场景

| 故障类型 | 优先级 | 应急目标 |
|----------|--------|----------|
| 服务崩溃 | P0 | 5分钟内恢复 |
| 数据库故障 | P0 | 10分钟内恢复 |
| 外部依赖故障 | P1 | 30分钟内降级 |
| 数据丢失 | P1 | 1小时内恢复 |
| 安全攻击 | P0 | 立即响应 |

---

## 二、性能优化计划（第一阶段：第1-2周）

### 2.1 数据库优化

#### 2.1.1 SQL查询优化
**目标**: 减少查询时间50%

**任务清单**:
- [ ] 分析慢查询日志
- [ ] 为常用查询添加索引
- [ ] 优化JOIN查询
- [ ] 实现查询缓存

**具体操作**:
```sql
-- 1. 分析慢查询
EXPLAIN QUERY PLAN SELECT * FROM admission_scores WHERE province = '广东';

-- 2. 添加索引
CREATE INDEX idx_province ON admission_scores(province);
CREATE INDEX idx_university ON admission_scores(university_name);
CREATE INDEX idx_year ON admission_scores(year);

-- 3. 优化查询
-- 避免 SELECT *，只查询需要的字段
SELECT university_name, major_name, score 
FROM admission_scores 
WHERE province = '广东' AND year = 2025;
```

#### 2.1.2 连接池配置
**目标**: 提高并发处理能力

**配置调整**:
```python
# configs/.config.yaml
database:
  pool_size: 20  # 连接池大小
  max_overflow: 30  # 最大溢出连接
  pool_timeout: 30  # 连接超时
  pool_recycle: 1800  # 连接回收时间
```

### 2.2 缓存优化

#### 2.2.1 Redis缓存策略
**目标**: 提高缓存命中率至80%

**任务清单**:
- [ ] 分析热点数据
- [ ] 设计缓存策略
- [ ] 实现缓存预热
- [ ] 监控缓存命中率

**缓存策略**:
```python
# 缓存分层
CACHE_LAYERS = {
    "L1": {
        "type": "memory",
        "ttl": 300,  # 5分钟
        "max_size": 1000
    },
    "L2": {
        "type": "redis",
        "ttl": 3600,  # 1小时
        "max_size": 10000
    }
}

# 热点数据缓存
HOT_DATA_CACHE = {
    "university_list": {"ttl": 1800, "key": "uni:list"},
    "major_categories": {"ttl": 3600, "key": "major:categories"},
    "province_data": {"ttl": 1800, "key": "province:{id}"}
}
```

### 2.3 代码优化

#### 2.3.1 Python性能分析
**目标**: 识别性能瓶颈，优化关键路径

**任务清单**:
- [ ] 使用cProfile分析性能
- [ ] 优化数据处理逻辑
- [ ] 实现异步处理
- [ ] 减少内存占用

**性能分析命令**:
```bash
# 分析API性能
python -m cProfile -o profile_output.prof -m api.main

# 分析特定函数
python -c "
import cProfile
from tools.sql_tools import SQLTools
cProfile.run('SQLTools.query_admission_scores(\"广东\")', 'sql_profile')
"

# 查看分析结果
python -c "
import pstats
p = pstats.Stats('profile_output.prof')
p.sort_stats('cumulative').print_stats(20)
"
```

#### 2.3.2 异步处理优化
**目标**: 提高并发处理能力

**实现方案**:
```python
# 使用asyncio优化IO密集型任务
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 线程池配置
executor = ThreadPoolExecutor(max_workers=10)

async def process_user_query(query):
    # 并行执行多个数据查询
    tasks = [
        asyncio.create_task(query_database(query)),
        asyncio.create_task(query_rag(query)),
        asyncio.create_task(query_neo4j(query))
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return combine_results(results)
```

### 2.4 架构优化

#### 2.4.1 负载均衡
**目标**: 支持100并发用户

**方案**:
```yaml
# docker-compose.yml 扩展
services:
  api:
    deploy:
      replicas: 3  # 3个API实例
    
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - api
```

**Nginx配置**:
```nginx
upstream api_backend {
    least_conn;
    server api:8000 weight=1;
    server api:8000 weight=1;
    server api:8000 weight=1;
}

server {
    listen 80;
    
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 2.4.2 微服务拆分
**目标**: 提高系统可扩展性

**拆分方案**:
```
原有单体架构 → 微服务架构
├── user-service (用户服务)
├── chat-service (对话服务)
├── data-service (数据服务)
├── rag-service (RAG服务)
└── gateway-service (网关服务)
```

### 2.5 资源优化

#### 2.5.1 服务器资源配置
**目标**: CPU占用<70%，内存占用<80%

**监控脚本**:
```python
# scripts/monitor_resources.py
import psutil
import time

def monitor_resources():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        print(f"CPU: {cpu_percent}%")
        print(f"内存: {memory.percent}%")
        print(f"可用内存: {memory.available / 1024 / 1024:.2f} MB")
        
        # 告警阈值
        if cpu_percent > 70:
            print("⚠️ CPU使用率过高")
        if memory.percent > 80:
            print("⚠️ 内存使用率过高")
        
        time.sleep(5)

if __name__ == "__main__":
    monitor_resources()
```

#### 2.5.2 容器资源限制
**配置**:
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

---

## 三、故障应急预案（第二阶段：第3-4周）

### 3.1 服务崩溃恢复

#### 3.1.1 自动重启机制
**目标**: 5分钟内恢复服务

**Systemd配置**:
```ini
# /etc/systemd/system/zx-ai-advisor.service
[Unit]
Description=小乐AI 高考志愿填报助手
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/zx_ai_advisor
ExecStart=/opt/zx_ai_advisor/venv/bin/python -m api.main
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
```

**健康检查脚本**:
```bash
#!/bin/bash
# scripts/health_check.sh

HEALTH_URL="http://127.0.0.1:8000/healthz"
MAX_RETRIES=3
RETRY_INTERVAL=10

check_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
    if [ $response -eq 200 ]; then
        echo "✅ 服务正常"
        return 0
    else
        echo "❌ 服务异常: HTTP $response"
        return 1
    fi
}

restart_service() {
    echo "🔄 正在重启服务..."
    systemctl restart zx-ai-advisor
    sleep 10
    
    if check_health; then
        echo "✅ 服务重启成功"
    else
        echo "❌ 服务重启失败，需要人工干预"
        exit 1
    fi
}

# 主逻辑
for i in $(seq 1 $MAX_RETRIES); do
    if check_health; then
        exit 0
    fi
    
    if [ $i -lt $MAX_RETRIES ]; then
        echo "⏳ 等待 $RETRY_INTERVAL 秒后重试..."
        sleep $RETRY_INTERVAL
    fi
done

# 所有重试失败，重启服务
restart_service
```

#### 3.1.2 日志收集
**配置ELK日志系统**:

**Filebeat配置**:
```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/zx_ai_advisor/logs/*.log
  fields:
    service: xiaole-ai
    environment: production

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "xiaole-ai-%{+yyyy.MM.dd}"

setup.template.name: "xiaole-ai"
setup.template.pattern: "xiaole-ai-*"
```

### 3.2 数据库故障恢复

#### 3.2.1 SQLite备份策略
**目标**: 10分钟内恢复数据

**备份脚本**:
```bash
#!/bin/bash
# scripts/backup_sqlite.sh

BACKUP_DIR="/opt/backups/sqlite"
DB_FILE="/opt/zx_ai_advisor/data/zx_advisor.db"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
cp $DB_FILE "$BACKUP_DIR/zx_advisor_$DATE.db"

# 压缩备份
gzip "$BACKUP_DIR/zx_advisor_$DATE.db"

# 保留最近30天备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "✅ SQLite备份完成: zx_advisor_$DATE.db.gz"
```

**恢复流程**:
```bash
# 1. 停止服务
systemctl stop zx-ai-advisor

# 2. 恢复数据库
gunzip -c /opt/backups/sqlite/zx_advisor_20260624_120000.db.gz > /opt/zx_ai_advisor/data/zx_advisor.db

# 3. 启动服务
systemctl start zx-ai-advisor

# 4. 验证恢复
curl http://127.0.0.1:8000/healthz
```

#### 3.2.2 Neo4j故障恢复
**Docker备份**:
```bash
# 备份Neo4j
docker exec neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/backups/

# 复制备份文件
docker cp neo4j:/var/lib/neo4j/backups/ ./neo4j-backups/

# 恢复Neo4j
docker exec neo4j neo4j-admin database load neo4j --from-path=/var/lib/neo4j/backups/
```

#### 3.2.3 Redis故障恢复
**配置持久化**:
```conf
# redis.conf
save 900 1
save 300 10
save 60 10000

appendonly yes
appendfsync everysec
```

**恢复流程**:
```bash
# 1. 停止Redis
redis-cli shutdown

# 2. 恢复数据
cp /opt/backups/redis/dump.rdb /var/lib/redis/dump.rdb

# 3. 启动Redis
redis-server /etc/redis/redis.conf
```

### 3.3 外部依赖故障应对

#### 3.3.1 LLM API故障降级
**目标**: 30分钟内切换到备用模型

**降级策略**:
```python
# core/fallback_manager.py
class LLMFallbackManager:
    def __init__(self):
        self.providers = [
            {"name": "MiMo", "priority": 1, "status": "active"},
            {"name": "DeepSeek", "priority": 2, "status": "active"},
            {"name": "Qwen", "priority": 3, "status": "active"},
            {"name": "GLM", "priority": 4, "status": "active"}
        ]
        self.current_provider = 0
    
    async def get_llm_response(self, prompt):
        for i in range(len(self.providers)):
            provider = self.providers[self.current_provider]
            
            try:
                response = await self._call_provider(provider["name"], prompt)
                return response
            except Exception as e:
                print(f"❌ {provider['name']} 调用失败: {e}")
                provider["status"] = "error"
                self.current_provider = (self.current_provider + 1) % len(self.providers)
        
        raise Exception("所有LLM提供商都不可用")
```

#### 3.3.2 搜索引擎故障应对
**备用搜索源**:
```python
# tools/web_search_tools.py
class WebSearchTools:
    def __init__(self):
        self.search_engines = [
            {"name": "DuckDuckGo", "priority": 1},
            {"name": "Metaso", "priority": 2},
            {"name": "Tavily", "priority": 3}
        ]
    
    async def search(self, query):
        for engine in self.search_engines:
            try:
                results = await self._search_with_engine(engine["name"], query)
                if results:
                    return results
            except Exception as e:
                print(f"❌ {engine['name']} 搜索失败: {e}")
                continue
        
        return []  # 返回空结果，不阻断服务
```

### 3.4 数据备份恢复

#### 3.4.1 全量备份策略
**每日备份**:
```bash
#!/bin/bash
# scripts/daily_backup.sh

DATE=$(date +%Y%m%d)
BACKUP_ROOT="/opt/backups/daily/$DATE"

# 创建备份目录
mkdir -p $BACKUP_ROOT/{sqlite,neo4j,redis,config}

# 1. SQLite备份
cp /opt/zx_ai_advisor/data/zx_advisor.db $BACKUP_ROOT/sqlite/

# 2. Neo4j备份
docker exec neo4j neo4j-admin database dump neo4j --to-path=/var/lib/neo4j/backups/
docker cp neo4j:/var/lib/neo4j/backups/ $BACKUP_ROOT/neo4j/

# 3. Redis备份
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_ROOT/redis/

# 4. 配置文件备份
cp /opt/zx_ai_advisor/.env $BACKUP_ROOT/config/
cp /opt/zx_ai_advisor/configs/.config.yaml $BACKUP_ROOT/config/

# 5. 压缩备份
tar -czf "/opt/backups/xiaole-ai-backup-$DATE.tar.gz" -C /opt/backups/daily $DATE

# 6. 上传到云存储（可选）
# aws s3 cp "/opt/backups/xiaole-ai-backup-$DATE.tar.gz" s3://your-bucket/backups/

echo "✅ 全量备份完成: xiaole-ai-backup-$DATE.tar.gz"
```

#### 3.4.2 增量备份
**每小时备份**:
```bash
#!/bin/bash
# scripts/incremental_backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/incremental"

mkdir -p $BACKUP_DIR

# 只备份变化的文件
rsync -avz --delete \
    /opt/zx_ai_advisor/data/ \
    $BACKUP_DIR/data_$DATE/

# 清理7天前的增量备份
find $BACKUP_DIR -name "data_*" -mtime +7 -delete

echo "✅ 增量备份完成: data_$DATE"
```

### 3.5 安全事件响应

#### 3.5.1 DDoS攻击防护
**Nginx限流配置**:
```nginx
http {
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    
    server {
        # API限流
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_conn addr 10;
            
            proxy_pass http://api_backend;
        }
        
        # 登录接口限流
        location /auth/login {
            limit_req zone=api burst=5 nodelay;
            
            proxy_pass http://api_backend;
        }
    }
}
```

#### 3.5.2 SQL注入防护
**参数化查询**:
```python
# 安全查询示例
def safe_query(province, year):
    # ❌ 危险：字符串拼接
    # query = f"SELECT * FROM admission_scores WHERE province = '{province}'"
    
    # ✅ 安全：参数化查询
    query = "SELECT * FROM admission_scores WHERE province = ? AND year = ?"
    cursor.execute(query, (province, year))
    return cursor.fetchall()
```

#### 3.5.3 恶意登录防护
**登录失败限制**:
```python
# core/auth.py
from datetime import datetime, timedelta
from collections import defaultdict

class LoginProtector:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.max_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
    
    def is_locked(self, ip):
        if ip not in self.failed_attempts:
            return False
        
        # 清理过期记录
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip]
            if attempt > datetime.now() - self.lockout_duration
        ]
        
        return len(self.failed_attempts[ip]) >= self.max_attempts
    
    def record_failed_attempt(self, ip):
        self.failed_attempts[ip].append(datetime.now())
    
    def get_remaining_lockout_time(self, ip):
        if not self.is_locked(ip):
            return 0
        
        oldest_attempt = min(self.failed_attempts[ip])
        unlock_time = oldest_attempt + self.lockout_duration
        remaining = unlock_time - datetime.now()
        
        return max(0, remaining.seconds)
```

---

## 四、监控体系建设

### 4.1 ELK日志系统部署

#### 4.1.1 Elasticsearch配置
```yaml
# docker-compose-elk.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.10.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  logstash:
    image: docker.elastic.co/logstash/logstash:8.10.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

#### 4.1.2 Logstash配置
```conf
# logstash.conf
input {
  file {
    path => "/opt/zx_ai_advisor/logs/*.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:message}" }
  }
  
  date {
    match => [ "timestamp", "ISO8601" ]
  }
  
  if [level] == "ERROR" {
    mutate { add_tag => ["error"] }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "xiaole-ai-%{+YYYY.MM.dd}"
  }
}
```

### 4.2 性能监控指标

#### 4.2.1 关键指标
```python
# scripts/performance_metrics.py
import psutil
import time
import json
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
    
    def collect_metrics(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": psutil.net_io_counters()._asdict(),
            "process_count": len(psutil.pids())
        }
    
    def save_metrics(self, metrics):
        self.metrics.append(metrics)
        
        # 保存到文件
        with open("logs/performance_metrics.json", "a") as f:
            f.write(json.dumps(metrics) + "\n")
        
        # 检查告警阈值
        self.check_alerts(metrics)
    
    def check_alerts(self, metrics):
        alerts = []
        
        if metrics["cpu_percent"] > 70:
            alerts.append(f"⚠️ CPU使用率过高: {metrics['cpu_percent']}%")
        
        if metrics["memory_percent"] > 80:
            alerts.append(f"⚠️ 内存使用率过高: {metrics['memory_percent']}%")
        
        if metrics["disk_usage"] > 90:
            alerts.append(f"⚠️ 磁盘使用率过高: {metrics['disk_usage']}%")
        
        if alerts:
            self.send_alerts(alerts)
    
    def send_alerts(self, alerts):
        # 发送告警通知
        for alert in alerts:
            print(alert)
            # 这里可以集成邮件、钉钉、企业微信等通知
    
    def run(self, interval=60):
        print("📊 性能监控启动...")
        while True:
            metrics = self.collect_metrics()
            self.save_metrics(metrics)
            time.sleep(interval)

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.run()
```

### 4.3 告警规则

#### 4.3.1 告警阈值
```yaml
# configs/alert_rules.yaml
alerts:
  cpu_high:
    threshold: 70
    duration: "5m"
    severity: "warning"
    message: "CPU使用率超过70%"
  
  memory_high:
    threshold: 80
    duration: "5m"
    severity: "warning"
    message: "内存使用率超过80%"
  
  disk_high:
    threshold: 90
    duration: "10m"
    severity: "critical"
    message: "磁盘使用率超过90%"
  
  error_rate_high:
    threshold: 5
    duration: "1m"
    severity: "critical"
    message: "错误率超过5%"
  
  response_time_high:
    threshold: 2000
    duration: "5m"
    severity: "warning"
    message: "响应时间超过2秒"
```

---

## 五、日常运维流程

### 5.1 每日检查清单

```bash
#!/bin/bash
# scripts/daily_check.sh

echo "🔍 小乐AI 每日检查"
echo "=================="

# 1. 服务状态检查
echo "1. 服务状态检查"
systemctl status zx-ai-advisor --no-pager

# 2. 健康检查
echo "2. 健康检查"
curl -s http://127.0.0.1:8000/healthz | jq .

# 3. 资源使用检查
echo "3. 资源使用检查"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "内存: $(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2}')"
echo "磁盘: $(df -h / | awk 'NR==2{print $5}')"

# 4. 日志检查
echo "4. 日志检查"
tail -20 /opt/zx_ai_advisor/logs/app.log | grep -i error

# 5. 备份检查
echo "5. 备份检查"
ls -lh /opt/backups/daily/ | tail -5

# 6. SSL证书检查
echo "6. SSL证书检查"
echo | openssl s_client -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

echo "✅ 每日检查完成"
```

### 5.2 每周维护任务

```bash
#!/bin/bash
# scripts/weekly_maintenance.sh

echo "🔧 小乐AI 每周维护"
echo "=================="

# 1. 清理日志文件
echo "1. 清理日志文件"
find /opt/zx_ai_advisor/logs -name "*.log" -mtime +30 -delete

# 2. 清理临时文件
echo "2. 清理临时文件"
find /tmp -name "xiaole-*" -mtime +7 -delete

# 3. 数据库优化
echo "3. 数据库优化"
sqlite3 /opt/zx_ai_advisor/data/zx_advisor.db "VACUUM; ANALYZE;"

# 4. 更新依赖
echo "4. 更新依赖"
cd /opt/zx_ai_advisor
source venv/bin/activate
pip list --outdated

# 5. 安全更新
echo "5. 安全更新"
apt list --upgradable 2>/dev/null | grep -i security

# 6. 备份验证
echo "6. 备份验证"
latest_backup=$(ls -t /opt/backups/daily/ | head -1)
echo "最新备份: $latest_backup"

echo "✅ 每周维护完成"
```

### 5.3 每月优化任务

```bash
#!/bin/bash
# scripts/monthly_optimization.sh

echo "📈 小乐AI 每月优化"
echo "=================="

# 1. 性能分析
echo "1. 性能分析"
python scripts/performance_analysis.py

# 2. 数据库分析
echo "2. 数据库分析"
sqlite3 /opt/zx_ai_advisor/data/zx_advisor.db "
SELECT name, COUNT(*) as count 
FROM sqlite_master 
WHERE type='table' 
GROUP BY name;"

# 3. 缓存分析
echo "3. 缓存分析"
redis-cli info stats | grep -E "hits|misses"

# 4. 安全审计
echo "4. 安全审计"
grep -i "failed" /opt/zx_ai_advisor/logs/app.log | wc -l

# 5. 容量规划
echo "5. 容量规划"
df -h
du -sh /opt/zx_ai_advisor/data/*

echo "✅ 每月优化完成"
```

---

## 六、执行时间表

### 第一阶段：性能优化（第1-2周）

| 任务 | 负责人 | 开始时间 | 结束时间 | 状态 |
|------|--------|----------|----------|------|
| 数据库索引优化 | 运维工程师 | 第1天 | 第3天 | 待执行 |
| Redis缓存配置 | 运维工程师 | 第2天 | 第4天 | 待执行 |
| Python性能分析 | 开发工程师 | 第3天 | 第5天 | 待执行 |
| 异步处理优化 | 开发工程师 | 第4天 | 第7天 | 待执行 |
| 负载均衡配置 | 运维工程师 | 第5天 | 第8天 | 待执行 |
| 资源监控部署 | 运维工程师 | 第6天 | 第10天 | 待执行 |
| 性能测试 | 测试工程师 | 第8天 | 第14天 | 待执行 |

### 第二阶段：故障应急（第3-4周）

| 任务 | 负责人 | 开始时间 | 结束时间 | 状态 |
|------|--------|----------|----------|------|
| 自动重启配置 | 运维工程师 | 第15天 | 第17天 | 待执行 |
| 数据库备份策略 | 运维工程师 | 第16天 | 第18天 | 待执行 |
| LLM降级策略 | 开发工程师 | 第17天 | 第20天 | 待执行 |
| 安全防护配置 | 安全工程师 | 第18天 | 第22天 | 待执行 |
| ELK日志系统 | 运维工程师 | 第20天 | 第25天 | 待执行 |
| 监控告警配置 | 运维工程师 | 第22天 | 第27天 | 待执行 |
| 应急演练 | 全体 | 第25天 | 第28天 | 待执行 |

---

## 七、成功指标

### 7.1 性能指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| 响应时间 | <2秒 | API响应时间监控 |
| 并发用户 | ≥100 | 压力测试 |
| CPU占用 | <70% | 系统监控 |
| 内存占用 | <80% | 系统监控 |
| 缓存命中率 | ≥80% | Redis监控 |

### 7.2 可用性指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| 服务可用性 | ≥99.5% | 健康检查 |
| 故障恢复时间 | <5分钟 | 故障演练 |
| 数据备份成功率 | 100% | 备份验证 |
| 安全事件响应时间 | <15分钟 | 安全审计 |

---

## 八、附录

### 8.1 常用命令速查

```bash
# 服务管理
systemctl start zx-ai-advisor
systemctl stop zx-ai-advisor
systemctl restart zx-ai-advisor
systemctl status zx-ai-advisor

# 日志查看
tail -f /opt/zx_ai_advisor/logs/app.log
grep -i error /opt/zx_ai_advisor/logs/app.log

# 数据库操作
sqlite3 /opt/zx_ai_advisor/data/zx_advisor.db
.backup /opt/backups/sqlite/backup.db

# Redis操作
redis-cli
redis-cli info stats
redis-cli monitor

# 性能监控
top
htop
vmstat 1
iostat -x 1
```

### 8.2 故障排查流程图

```
用户报告问题
    ↓
检查服务状态
    ↓
服务正常？ → 否 → 重启服务
    ↓ 是
检查日志
    ↓
有错误日志？ → 是 → 分析错误原因
    ↓ 否
检查资源使用
    ↓
资源过高？ → 是 → 优化资源配置
    ↓ 否
检查网络连接
    ↓
网络正常？ → 否 → 检查网络配置
    ↓ 是
联系技术支持
```

### 8.3 应急联系人

| 角色 | 联系人 | 联系方式 | 职责 |
|------|--------|----------|------|
| 运维负责人 | 待指定 | 待填写 | 服务稳定性 |
| 开发负责人 | 待指定 | 待填写 | 代码问题 |
| 安全负责人 | 待指定 | 待填写 | 安全事件 |
| 产品经理 | 待指定 | 待填写 | 业务影响 |

---

*计划制定完成 · 小乐AI 运行和维护计划 · 版本: v1.0*