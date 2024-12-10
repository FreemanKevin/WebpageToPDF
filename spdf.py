import os
import time
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

def sanitize_filename(filename):
    """
    清理文件名中的非法字符，确保文件名合法。
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename.strip()

def save_pdf_from_url(url, save_path):
    """
    从给定 URL 使用 WebDriver 生成 PDF 并保存到指定路径。
    """
    driver = None
    try:
        driver = setup_driver()  # 初始化 WebDriver
        print(f"正在处理：{url}")
        driver.get(url)

        # 等待页面加载完成
        time.sleep(10)
        if driver.execute_script("return document.readyState") != "complete":
            print(f"页面加载未完成：{url}")
            return

        # 获取网页标题作为文件名
        title = sanitize_filename(driver.title) or "Untitled"
        pdf_name = f"{title}.pdf"
        pdf_path = os.path.join(save_path, pdf_name)

        # 使用 CDP 命令打印页面为 PDF
        print_options = {
            'landscape': True,
            'displayHeaderFooter': False,
            'printBackground': True,
            'preferCSSPageSize': True,
            'paperWidth': 8.27,
            'paperHeight': 11.69,
            'marginTop': 0,
            'marginBottom': 0,
            'marginLeft': 0,
            'marginRight': 0,
            'scale': 1.0,
        }
        result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
        if 'data' in result:
            pdf_data = base64.b64decode(result['data'])
            with open(pdf_path, 'wb') as f:
                f.write(pdf_data)
            print(f"PDF 已保存：{pdf_path}")
        else:
            print(f"未能获取 PDF 数据：{url}")
    except WebDriverException as e:
        print(f"WebDriver 出错，URL: {url}, 错误信息: {e}")
    except Exception as e:
        print(f"处理失败：{url}, 错误信息：{str(e)}")
    finally:
        if driver:
            driver.quit()  # 确保 WebDriver 被释放

def setup_driver():
    """
    配置并初始化 WebDriver。
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    prefs = {
        'printing.print_preview_sticky_settings.appState': json.dumps({
            'recentDestinations': [{'id': 'Save as PDF', 'origin': 'local'}],
            'selectedDestinationId': 'Save as PDF',
            'version': 2
        })
    }
    chrome_options.add_experimental_option('prefs', prefs)

    service = Service(executable_path="C:\\soft\\chromedriver-win64\\chromedriver.exe")
    driver = None
    retries = 3
    for _ in range(retries):
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except WebDriverException as e:
            print(f"WebDriver 启动失败，重试中... 错误信息：{e}")
            time.sleep(2)
    raise RuntimeError("WebDriver 启动失败，已超出最大重试次数")

def export_pdfs_from_urls(url_file, max_workers=4):
    """
    从文件中的 URL 列表并发生成 PDF。
    """
    save_path = os.getcwd()
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for url in urls:
            futures.append(executor.submit(save_pdf_from_url, url, save_path))

        # 等待所有任务完成并处理结果
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"任务出错，错误信息：{e}")

if __name__ == "__main__":
    url_file = "urls.txt"  # 包含 URL 列表的文件
    export_pdfs_from_urls(url_file)
