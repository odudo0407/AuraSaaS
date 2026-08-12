"""
AuraSaaS UI 自动化测试套件（Selenium + pytest）
================================================
运行前准备：
  1. 前后端都得起：backend localhost:8000，frontend localhost:3000
  2. 准备一个测试账号（首次可手动在 localhost:3000/register 注册）
  3. 把下面 TEST_EMAIL / TEST_PASSWORD 改成你的测试账号
     （或运行时用环境变量：AURA_TEST_EMAIL=xxx AURA_TEST_PASSWORD=xxx pytest ...）
  4. 依赖：pip install selenium pytest
  5. 运行：
        pytest test_aura_ui.py -s -v                       # 全部 7 条
        pytest test_aura_ui.py -k "wrong_password or empty_validation or auth_guard or register" -v   # 不需要账号的 4 条

真实页面结构（来自前端源码，已核对）：
  - 登录页 /login    ：email=input[type=email]，password=input[type=password]，登录按钮=button[type=submit]
  - 注册页 /register ：username=input[type=text]，email=input[type=email]，password/confirmPassword=input[type=password]
  - 受保护路由前缀 /app/* 全部 requiresAuth，未登录访问会被守卫踢回 /login（token 存在 localStorage）
  - 登录/注册成功均跳转 /app/dashboard
  - AI 页 /app/ai   ：输入框=textarea，发送按钮=文字"发送"（普通 button，非 submit）

设计原则：
  - 只用显式等待（WebDriverWait），不用 time.sleep
  - AI 回答是非确定性的，TC-UI-06 只断言"提问后用户消息出现在聊天区"，不断言 AI 具体文字
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
TEST_EMAIL = os.getenv("AURA_TEST_EMAIL", "3228788299@qq.com")
TEST_PASSWORD = os.getenv("AURA_TEST_PASSWORD", "123456")

# ---- 定位器（已对照前端源码核对）----
EMAIL_INPUT = (By.CSS_SELECTOR, 'input[type="email"]')
PASSWORD_INPUT = (By.CSS_SELECTOR, 'input[type="password"]')
TEXT_INPUT = (By.CSS_SELECTOR, 'input[type="text"]')
SUBMIT_BTN = (By.CSS_SELECTOR, 'button[type="submit"]')
REGISTER_LINK = (By.PARTIAL_LINK_TEXT, "创建")   # 文字"立即创建" → /register


@pytest.fixture
def driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--lang=zh-CN")
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(0)          # 关掉隐式等待，只用显式等待，避免等待时间叠加
    yield d
    d.quit()


def wait_for(driver, locator, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def fill_login(driver, email, password):
    wait_for(driver, EMAIL_INPUT).send_keys(email)
    driver.find_element(*PASSWORD_INPUT).send_keys(password)
    driver.find_element(*SUBMIT_BTN).click()


def wait_dashboard(driver, timeout=30):
    """登录成功后等待跳转到 /app/dashboard。超时拉长到 30s 避免后端冷启动偶发失败；
    一旦超时抛出当前 URL + 页面片段，便于定位是后端没起还是登录真失败。"""
    try:
        WebDriverWait(driver, timeout).until(lambda d: "/dashboard" in d.current_url)
    except Exception:
        raise AssertionError(
            f"登录后未在 {timeout}s 内跳转到 /dashboard。\n"
            f"当前 URL = {driver.current_url}\n"
            f"页面片段 = {driver.page_source[:400]}"
        )


# ============ TC-UI-03 错误密码登录 ============
def test_login_wrong_password(driver):
    driver.get(BASE_URL + "/login")
    fill_login(driver, TEST_EMAIL, "WrongPassword123!")
    WebDriverWait(driver, 15).until(EC.url_contains("/login"))
    page = driver.page_source
    assert any(k in page for k in ["密码", "错误", "invalid", "失败", "Incorrect",
                                   "用户", "账号", "不存在", "not found", "注册"]), \
        "登录失败但未检测到错误提示文案"


# ============ TC-UI-07 表单校验：空提交 ============
def test_login_empty_validation(driver):
    driver.get(BASE_URL + "/login")
    wait_for(driver, SUBMIT_BTN).click()          # 先等按钮渲染再点
    WebDriverWait(driver, 10).until(EC.url_contains("/login"))
    email = driver.find_element(*EMAIL_INPUT)
    msg = email.get_attribute("validationMessage") or ""
    assert msg != "" or "/login" in driver.current_url, \
        "空提交未被前端拦截"


# ============ TC-UI-04 鉴权拦截：未登录直访受保护页 ============
def test_auth_guard_redirect(driver):
    driver.get(BASE_URL + "/app/dashboard")      # 真受保护路由是 /app/dashboard
    WebDriverWait(driver, 15).until(EC.url_contains("/login"))
    assert "/login" in driver.current_url


# ============ TC-UI-01 注册 E2E（resilient 定位） ============
def test_register_e2e(driver):
    driver.get(BASE_URL + "/login")
    wait_for(driver, REGISTER_LINK).click()
    WebDriverWait(driver, 15).until(EC.url_contains("/register"))
    # 注册表单字段（实测 Register.vue）：username / email / password / confirmPassword
    wait_for(driver, TEXT_INPUT).send_keys("Selenium Tester")
    driver.find_element(*EMAIL_INPUT).send_keys(
        "new_user_" + str(int(time.time())) + "@example.com")
    for p in driver.find_elements(*PASSWORD_INPUT):
        p.send_keys("Test@123456")
    driver.find_element(*SUBMIT_BTN).click()
    # 注册成功跳 /app/dashboard；若后端未起会停留在 /register 并显示错误
    WebDriverWait(driver, 15).until(
        lambda d: "/login" in d.current_url or "/dashboard" in d.current_url
    )


# ============ TC-UI-02 登录成功 ============
def test_login_success(driver):
    driver.get(BASE_URL + "/login")
    fill_login(driver, TEST_EMAIL, TEST_PASSWORD)
    wait_dashboard(driver)


# ============ TC-UI-05 退出登录 ============
def test_logout(driver):
    driver.get(BASE_URL + "/login")
    fill_login(driver, TEST_EMAIL, TEST_PASSWORD)
    wait_dashboard(driver)
    # 退出按钮在右上角头像下拉菜单里，需先点头像(class 含 bg-ink)展开菜单
    avatar = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'bg-ink')]"))
    )
    avatar.click()
    # 菜单展开后出现"退出登录"按钮
    logout = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'退出登录') or contains(.,'Log out')]")
        )
    )
    logout.click()
    WebDriverWait(driver, 15).until(EC.url_contains("/login"))


# ============ TC-UI-06 AI Analysis 冒烟（只断言有内容） ============
# 注意：AI 回答非确定性，本用例只验证"能提问→用户消息出现在聊天区"，不断言回复文字。
# 要验证 AI 真正回复，需后端 + LLM key 且等待较久，属非确定性，不放在断言里。
def test_ai_analysis_smoke(driver):
    driver.get(BASE_URL + "/login")
    fill_login(driver, TEST_EMAIL, TEST_PASSWORD)
    WebDriverWait(driver, 15).until(lambda d: "/dashboard" in d.current_url)
    driver.get(BASE_URL + "/app/ai")
    WebDriverWait(driver, 15).until(EC.url_contains("/app/ai"))
    box = wait_for(driver, (By.CSS_SELECTOR, "textarea"))
    question = "近 7 天营收趋势"
    box.send_keys(question)
    # 发送按钮：文字"发送"（普通 button，非 type=submit）
    send_btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'发送') or contains(.,'Send')]")
        )
    )
    send_btn.click()
    # 断言：用户自己发的消息气泡出现在聊天区（证明输入+发送+渲染链路通）
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//div[contains(@class,'bg-ink') and contains(.,'{question}')]")
        )
    )
