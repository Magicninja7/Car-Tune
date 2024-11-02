import pyautogui
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

def setup_driver():
    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Firefox(options=options)
    return driver

def get_current_word(driver):
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "u-pl-0"))
        )
        return element.text
    except Exception as e:
        print(f"Error getting text: {e}")
        return None

def type_with_faster_delay(text):
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.write(" ", interval=0.0001)

def main():
    pyautogui.FAILSAFE = True
    
    print("Setting up webdriver...")
    driver = setup_driver()
    if not driver:
        return
    
    website_url = "https://www.livechat.com/typing-speed-test/#/"
    driver.get(website_url)
    
    try:
        last_word = ""
        while True:
            current_word = get_current_word(driver)
            if current_word and current_word != last_word:
                type_with_faster_delay(current_word)
                last_word = current_word
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
