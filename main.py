import time
import os
import json
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from concurrent.futures import ProcessPoolExecutor
from webdriver_manager.chrome import ChromeDriverManager
import argparse
from urllib.parse import urlparse
from colorama import init, Fore, Style

init()  # 初始化colorama

class WebCrawler:
    def __init__(self, max_depth=3, delay=3, debug=False, visible=False):
        self.max_depth = max_depth
        self.delay = delay
        self.visited_urls = set()
        self.driver = None
        self.debug = debug
        self.visible = visible

    def setup_driver(self):
        """设置并返回WebDriver实例"""
        if self.driver:
            return self.driver

        chrome_options = Options()
        if not self.visible:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        prefs = {
            'printing.print_preview_sticky_settings.appState': json.dumps({
                'recentDestinations': [{'id': 'Save as PDF', 'origin': 'local'}],
                'selectedDestinationId': 'Save as PDF',
                'version': 2
            })
        }
        chrome_options.add_experimental_option('prefs', prefs)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            if self.debug:
                print("浏览器驱动初始化成功")
            return self.driver
        except Exception as e:
            if self.debug:
                print(f"使用系统 ChromeDriver 失败: {str(e)}")
            try:
                from webdriver_manager.core.os_manager import ChromeType
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                return self.driver
            except Exception as e2:
                if self.debug:
                    print(f"安装 ChromeDriver 失败: {str(e2)}")
                raise e2

    def get_page_title(self, driver):
        """获取页面标题"""
        try:
            # 尝试获取微信文章标题
            title = driver.find_element(By.CLASS_NAME, "rich_media_title").text.strip()
            if title:
                return title
        except:
            pass

        try:
            # 尝试获取h1标题
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
            if title:
                return title
        except:
            pass

        # 使用页面标题
        return driver.title.strip() or "未命名文章"

    def sanitize_filename(self, filename):
        """清理文件名中的非法字符"""
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        return "".join(x for x in filename if x.isalnum() or x in (' ', '-', '_')).strip()

    def save_page_as_pdf(self, url, save_dir):
        """将页面保存为PDF"""
        try:
            self.log_info(f"正在将页面转换为PDF: {url}")
            
            # 获取页面标题作为文件名
            title = self.sanitize_filename(self.get_page_title(self.driver))
            pdf_name = f"{title}.pdf"
            
            # 直接在当前目录保存PDF，不创建同名子目录
            pdf_path = os.path.join(save_dir, pdf_name)

            # 检查文件是否已存在
            if os.path.exists(pdf_path):
                self.log_warning(f"PDF已存在，跳过: {pdf_path}")
                return True

            print_options = {
                'landscape': False,
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
            result = self.driver.execute_cdp_cmd('Page.printToPDF', print_options)
            
            if 'data' in result:
                pdf_data = base64.b64decode(result['data'])
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_data)
                self.log_success(f"PDF已保存: {pdf_path}")
                return True
            return False
        except Exception as e:
            self.log_error(f"保存PDF时出错: {str(e)}")
            return False

    def is_valid_url(self, url):
        """检查URL是否有效且未访问过"""
        if not url:
            return False
        if url in self.visited_urls:
            return False
        if url.startswith(("javascript:", "void(0)", "#")):
            return False
        return True

    def get_domain(self, url):
        """获取URL的域名"""
        return urlparse(url).netloc

    def wait_for_login(self):
        """等待用户登录"""
        print("\n检测到需要登录...")
        print("请在打开的浏览器窗口中完成登录")
        print("登录成功后程序将自动继续")
        
        while True:
            try:
                # 检查是否存在微信文章的特征元素
                title = self.driver.find_element(By.CLASS_NAME, "rich_media_title")
                if title:
                    print("登录成功！继续处理...")
                    return True
            except:
                time.sleep(1)  # 每秒检查一次

    def check_article_migration(self, driver):
        """检查文章是否已迁移，如果是则获取新链接"""
        try:
            # 检查是否存在迁移提示文本
            migration_text = driver.find_elements(By.XPATH, "//*[contains(text(), '该公众号已迁移')]")
            if migration_text:
                self.log_warning("\n检测到文章已迁移...")
                
                try:
                    # 查找并点击"访问文章"按钮
                    article_button = driver.find_element(By.XPATH, "//a[contains(text(), '访问文章')]")
                    if article_button:
                        self.log_success("找到'访问文章'按钮，尝试获取新链接...")
                        
                        # 获取按钮的href属性
                        new_url = article_button.get_attribute("href")
                        if not new_url:
                            # 如果按钮本身没有href，尝试获取父元素的href
                            parent = article_button.find_element(By.XPATH, "./..")
                            new_url = parent.get_attribute("href")
                        
                        if new_url:
                            self.log_box(f"新链接: {new_url}")
                            self.log_warning("请更新urls.txt中的链接后重试。")
                            return new_url
                        else:
                            self.log_error("未能获取新的文章链接")
                            return None
                except Exception as e:
                    self.log_error(f"获取新链接时出错: {str(e)}")
                    return None
        except Exception as e:
            self.log_error(f"检查文章迁移时出错: {str(e)}")
            return None
        return None

    def crawl_page(self, url, current_depth=0, parent_dir="pdfs"):
        """递归爬取页面"""
        if current_depth > self.max_depth or url in self.visited_urls:
            self.log_debug(f"跳过URL (深度: {current_depth}): {url}")
            return

        self.visited_urls.add(url)
        self.log_highlight(f"\n当前深度: {current_depth}, 处理页面: {url}")

        try:
            self.log_info("正在加载页面...")
            self.driver.get(url)
            self.log_success("页面加载完成，等待延迟...")
            time.sleep(self.delay)

            # 检查文章迁移
            new_url = self.check_article_migration(self.driver)
            if new_url:
                self.log_warning("\n文章已迁移，建议更新链接后重试")
                self.log_box(f"新链接: {new_url}")
                self.log_error("程序将退出...")
                sys.exit(1)

            # 检查登录状态
            try:
                self.log_info("检查是否需要登录...")
                self.driver.find_element(By.CLASS_NAME, "rich_media_title")
                self.log_success("找到文章标题，无需登录")
            except Exception as e:
                self.log_warning(f"未找到文章标题，可能需要登录: {str(e)}")
                self.wait_for_login()

            # 获取页面标题
            page_title = self.sanitize_filename(self.get_page_title(self.driver))
            self.log_highlight(f"页面标题: {page_title}")

            # 创建目录
            save_dir = os.path.join(parent_dir, page_title)
            os.makedirs(save_dir, exist_ok=True)
            self.log_info(f"创建目录: {save_dir}")

            # 保存PDF
            if self.save_page_as_pdf(url, save_dir):
                self.log_success("PDF保存成功")
            else:
                self.log_error("PDF保存失败")

            # 处理链接
            if current_depth >= self.max_depth:
                self.log_warning(f"已达到最大深度 {self.max_depth}，停止获取链接")
                return

            self.log_info("开始获取页面链接...")
            links = self.get_page_links(url)
            self.log_highlight(f"找到 {len(links)} 个有效链接")

            for i, link in enumerate(links, 1):
                self.log_highlight(f"\n处理链接 [{i}/{len(links)}]: {link}")
                self.crawl_page(link, current_depth + 1, save_dir)

        except Exception as e:
            self.log_error(f"处理页面时出错 {url}: {str(e)}")
            if self.debug:
                self.log_error("详细错误信息:")
                self.log_error(traceback.format_exc())

    def process_url(self, url):
        """处理单个起始URL"""
        try:
            print(f"\n开始处理URL: {url}")
            self.driver = self.setup_driver()
            print("浏览器驱动初始化成功")
            self.crawl_page(url)
        except Exception as e:
            print(f"处理URL时出错: {url}")
            print(f"错误信息: {str(e)}")
            import traceback
            print("详细错误信息:")
            print(traceback.format_exc())
        finally:
            if self.driver:
                print("关闭浏览器驱动")
                self.driver.quit()
                self.driver = None

    def log_info(self, message):
        """普通信息 - 白色"""
        print(f"{Style.RESET_ALL}{message}")

    def log_success(self, message):
        """成功信息 - 绿色"""
        print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

    def log_warning(self, message):
        """警告信息 - 黄色"""
        print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

    def log_error(self, message):
        """错误信息 - 红色"""
        print(f"{Fore.RED}{message}{Style.RESET_ALL}")

    def log_highlight(self, message):
        """重要信息 - 青色"""
        print(f"{Fore.CYAN}{Style.BRIGHT}{message}{Style.RESET_ALL}")

    def log_debug(self, message):
        """调试信息 - 灰色"""
        if self.debug:
            print(f"{Style.DIM}{message}{Style.RESET_ALL}")

    def log_box(self, message):
        """在方框中显示重要信息"""
        print("\n" + "="*80)
        print(f"{Style.BRIGHT}{message}{Style.RESET_ALL}")
        print("="*80 + "\n")

    def get_page_links(self, url):
        """获取页面中的所有有效链接"""
        links = []
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a")
            original_domain = self.get_domain(url)

            for element in elements:
                link = element.get_attribute("href")
                if self.is_valid_url(link) and self.get_domain(link) == original_domain:
                    links.append(link)
        except Exception as e:
            self.log_error(f"获取页面链接时出错: {str(e)}")
        
        return links

def main():
    """主程序入口"""
    # 设置颜色 - 统一使用浅红色
    text_color = Fore.LIGHTRED_EX + Style.BRIGHT
    reset = Style.RESET_ALL
    
    logo = fr'''
{text_color}
 _       __     __                         ______      ____  ____  _____ 
| |     / /__  / /_  ____  ____ _____ ___/_  __/___  / __ \/ __ \/ ___/
| | /| / / _ \/ __ \/ __ \/ __ `/ __ `/ _ \/ / / __ \/ /_/ / / / / __ \ 
| |/ |/ /  __/ /_/ / /_/ / /_/ / /_/ /  __/ / / /_/ / ____/ /_/ / /_/ / 
|__/|__/\___/_.___/ .___/\__,_/\__, /\___/_/  \____/_/   /_____/\____/  
                 /_/          /____/                                      
{reset}'''
    # 先打印 logo
    print(logo)
    print("\n")  # 添加两个空行
    
    parser = argparse.ArgumentParser(
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=50, width=120),
        epilog='''
示例:
  %(prog)s -d 3                     # 设置递归深度为3层
  %(prog)s -t 5                     # 设置页面加载延迟为5秒
  %(prog)s -d 2 -t 3 -D             # 递归2层，延迟3秒，显示调试信息
  %(prog)s -d 3 -v                  # 递归3层，显示浏览器窗口
  %(prog)s -D -v                    # 显示调试信息和浏览器窗口
''')
    
    # 使用 ArgumentDefaultsHelpFormatter 的方式来格式化参数说明
    parser._optionals.title = 'options'
    parser._action_groups[0].title = 'options'
    
    # 设置参数时指定对齐位置
    parser.add_argument('-d', '--depth',    type=int, default=3, metavar='num',
                      help='递归深度 (默认: 3)')
    parser.add_argument('-t', '--delay',    type=int, default=3, metavar='sec',
                      help='页面加载延迟秒数 (默认: 3)')
    parser.add_argument('-D', '--debug',    action='store_true',
                      help='启用调试模式，显示详细日志')
    parser.add_argument('-v', '--visible',  action='store_true',
                      help='显示浏览器窗口')
    args = parser.parse_args()

    if args.debug:
        print(f"开始运行... (最大深度: {args.depth}, 延迟: {args.delay}秒)")
    
    if not os.path.exists("urls.txt"):
        print("错误：urls.txt文件不存在！")
        return
    
    os.makedirs("pdfs", exist_ok=True)
    
    with open("urls.txt", "r") as file:
        urls = [line.strip() for line in file.readlines() if line.strip()]
        if args.debug:
            print(f"从urls.txt读取到 {len(urls)} 个URL")
            print("URLs:", urls)
    
    try:
        for url in urls:
            crawler = WebCrawler(max_depth=args.depth, delay=args.delay, 
                               debug=args.debug, visible=args.visible)
            try:
                crawler.process_url(url)
            except Exception as e:
                if args.debug:
                    print(f"处理URL时出错: {url}")
                    print(f"错误信息: {str(e)}")
                    import traceback
                    print("详细错误信息:")
                    print(traceback.format_exc())
                else:
                    print(f"处理URL失败: {url}")
    except Exception as e:
        if args.debug:
            print(f"程序运行出错: {str(e)}")
            import traceback
            print("详细错误信息:")
            print(traceback.format_exc())
        else:
            print("程序运行出错")
    
    if args.debug:
        print("\n所有任务处理完成！")

if __name__ == "__main__":
    main() 