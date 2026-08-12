from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

opts = Options()
opts.add_argument("--headless=new")

driver = webdriver.Chrome(options=opts)
try:
    driver.get("http://localhost:3000")
    print("当前 URL:", driver.current_url)
    print("页面标题:", driver.title)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "input"))
        )
        print("✅ 找到 input 数量:", len(driver.find_elements(By.TAG_NAME, "input")))
    except Exception:
        print("❌ 15 秒内根路径没等到 input，页面片段：")
        print(driver.page_source[:800])
        driver.get("http://localhost:3000/login")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "input"))
            )
            print("✅ 跳到 /login 后找到 input 数量:", len(driver.find_elements(By.TAG_NAME, "input")))
        except Exception:
            print("❌ /login 也没有 input，片段：")
            print(driver.page_source[:800])
finally:
    driver.quit()
