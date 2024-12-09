import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import json

def export_pdfs_from_urls(url_file):
    save_path = os.getcwd()

    # 简化Chrome配置
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')  # 添加此配置避免内存问题
    
    # 设置下载选项
    prefs = {
        'download.default_directory': save_path,
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,
        'printing.print_preview_sticky_settings.appState': json.dumps({
            'recentDestinations': [{'id': 'Save as PDF', 'origin': 'local'}],
            'selectedDestinationId': 'Save as PDF',
            'version': 2,
            'isHeaderFooterEnabled': False,
            'isCssBackgroundEnabled': True,
            'scaling': 100,
            'scalingType': 3,
            'isLandscapeEnabled': True,
            'mediaSize': {'height_microns': 297000, 'width_microns': 210000, 'name': 'ISO_A4'}
        })
    }
    chrome_options.add_experimental_option('prefs', prefs)

    # 初始化 WebDriver
    # ChromeDriver 下载地址 https://googlechromelabs.github.io/chrome-for-testing/
    service = Service(executable_path="D:\\data\\chromedriver-win64\\chromedriver.exe")  # 替换为你的 ChromeDriver 路径
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 从文件中读取 URL 列表
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]
    index = 0
    # 批量处理URL部分
    for url in urls:
        index += 1
        try:
            print(f"正在处理：{url}")
            driver.get(url)
            
            # 增加页面加载等待时间
            time.sleep(10)
            
            # 确保页面完全加载
            driver.execute_script("return document.readyState") == "complete"
            
            # pdf_name = url.split('/')[-1]
            # if not pdf_name.endswith('.pdf'):
            #     pdf_name = pdf_name + '.pdf'
            pdf_name = f"test{index}.pdf"
            pdf_path = os.path.join(save_path, pdf_name)
            
            # 使用CDP命令打印页面
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
                'returnAsStream': True  # 添加这个选项
            }
            
            result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
            
            if 'data' in result:
                import base64
                pdf_data = base64.b64decode(result['data'])  # 使用base64解码
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_data)
                print(f"PDF已保存：{pdf_path}")
            else:
                print(f"未能获取PDF数据：{url}")
            
        except Exception as e:
            print(f"处理失败：{url}")
            print(f"错误信息：{str(e)}")
            continue
            
    driver.quit()

if __name__ == "__main__":
    # 输入包含 URL 列表的文件路径
    url_file = "urls.txt"
    export_pdfs_from_urls(url_file)
