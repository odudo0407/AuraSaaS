from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

opts = Options()
opts.add_argument("--headless=new")
driver = webdriver.Chrome(options=opts)
try:
    driver.get("http://localhost:3000/login")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "input"))
    )
    print("=== INPUT 列表 ===")
    for i, el in enumerate(driver.find_elements(By.TAG_NAME, "input"), 1):
        print(f"[{i}] type={el.get_attribute('type')} id={el.get_attribute('id')} "
              f"name={el.get_attribute('name')} placeholder={el.get_attribute('placeholder')}")
    print("=== BUTTON 列表 ===")
    for i, el in enumerate(driver.find_elements(By.TAG_NAME, "button"), 1):
        print(f"[{i}] text={el.text!r} type={el.get_attribute('type')} id={el.get_attribute('id')}")
    print("=== A 链接列表 ===")
    for i, el in enumerate(driver.find_elements(By.TAG_NAME, "a"), 1):
        print(f"[{i}] text={el.text!r} href={el.get_attribute('href')}")
finally:
    driver.quit()
