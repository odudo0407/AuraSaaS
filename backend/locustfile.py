"""
Locust 性能测试 — AuraSaaS 核心接口压力测试

用法:
    cd backend
    locust -f locustfile.py --host http://127.0.0.1:8000

命令行无 UI 模式（50 并发，30 秒）:
    locust -f locustfile.py --host http://127.0.0.1:8000 \
        --headless --users 50 --spawn-rate 10 --run-time 30s \
        --html report.html
"""

from locust import HttpUser, task, between


class AuraSaaSUser(HttpUser):
    """模拟普通用户访问 AuraSaaS 核心接口"""
    wait_time = between(0.5, 1.5)

    @task
    def health_check(self):
        self.client.get("/api/health")
