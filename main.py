import sys
import signal

# 添加信号处理函数
def signal_handler(signum, frame):
    print("\n\n程序被用户中断，正在清理资源并退出...")
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)  # 处理 Ctrl+C
signal.signal(signal.SIGTERM, signal_handler) # 处理终止信号

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = {
        'selenium': 'selenium',
        'webdriver_manager': 'webdriver-manager',
        'colorama': 'colorama'
    }
    
    missing_packages = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("\n" + "="*80)
        print("错误：缺少必要的依赖包！")
        print("\n请运行以下命令安装依赖：")
        print(f"\npip install {' '.join(missing_packages)}")
        print("\n或者运行：")
        print("\npip install -r requirements.txt")
        print("="*80 + "\n")
        sys.exit(1)

# 在程序开始时检查依赖
check_dependencies()

import time
import os
import json
import base64
import traceback
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
        self._stop = False  # 添加停止标志

    def setup_driver(self):
        """设置并返回WebDriver实例"""
        if self.driver:
            return self.driver

        try:
            chrome_options = Options()
            if not self.visible:
                chrome_options.add_argument("--headless")
            
            # 添加以下选项来抑制不必要的错误信息
            chrome_options.add_argument("--log-level=3")  # 只显示致命错误
            chrome_options.add_argument("--silent")  # 静默模式
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 禁用 DevTools 日志
            
            # 其他选项保持不变
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
                    self.log_success("浏览器驱动初始化成功")
                return self.driver
            except Exception as e:
                if "chromedriver" in str(e).lower():
                    self.log_box(
                        "ChromeDriver初始化失败！\n\n"
                        "请检查：\n"
                        "1. Chrome浏览器是否已安装\n"
                        "2. 是否已安装所需Python包：pip install -r requirements.txt\n"
                        "3. 如果问题仍然存在，请尝试手动下载ChromeDriver：\n"
                        "   https://chromedriver.chromium.org/downloads"
                    )
                raise e

        except Exception as e:
            if self.debug:
                self.log_error(f"设置WebDriver时出错: {str(e)}")
                self.log_error(traceback.format_exc())
            else:
                self.log_error("浏览器驱动初始化失败，请检查Chrome浏览器是否正确安装")
            raise e

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
        """检查文章是否已迁移，如果是则获取并访问新链接"""
        try:
            # 检查是否存在迁移提示文本
            migration_text = driver.find_elements(By.XPATH, "//*[contains(text(), '该公众号已迁移')]")
            if migration_text:
                self.log_warning("\n检测到文章已迁移...")
                
                try:
                    # 查找并点击"访问文章"按钮
                    article_button = driver.find_element(By.XPATH, "//a[contains(text(), '访问文章')]")
                    if article_button:
                        self.log_success("找到'访问文章'按钮，正在跳转...")
                        
                        # 获取新链接
                        new_url = article_button.get_attribute("href")
                        if not new_url:
                            parent = article_button.find_element(By.XPATH, "./..")
                            new_url = parent.get_attribute("href")
                        
                        if new_url:
                            self.log_box(f"原文已迁移到新链接: {new_url}")
                            # 直接访问新链接
                            self.log_info("正在访问新链接...")
                            driver.get(new_url)
                            time.sleep(self.delay)  # 等待页面加载
                            return True
                        else:
                            self.log_error("未能获取新的文章链接")
                            return False
                except Exception as e:
                    self.log_error(f"处理文章迁移时出错: {str(e)}")
                    return False
        except Exception as e:
            self.log_error(f"检查文章迁移时出错: {str(e)}")
            return False
        return False

    def check_article_status(self, driver):
        """检查文章状态（是否被删除或失效）"""
        try:
            # 检查常见的错误提示
            error_patterns = [
                "该内容已被发布者删除",
                "此内容因违规无法查看",
                "该公众号已被屏蔽",
                "该内容已被投诉",
                "抱歉，此内容已被删除",
            ]
            
            for pattern in error_patterns:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{pattern}')]")
                if elements:
                    return False, pattern
                
            return True, None
            
        except Exception as e:
            self.log_error(f"检查文章状态时出错: {str(e)}")
            return False, str(e)

    def crawl_page(self, url, current_depth=0, parent_dir="pdfs"):
        """递归爬取页面"""
        try:
            if self._stop:  # 检查停止标志
                return

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

                # 检查文章状态
                is_valid, error_msg = self.check_article_status(self.driver)
                if not is_valid:
                    self.log_warning(f"文章无法访问: {error_msg}")
                    self.log_box(f"已跳过无效链接: {url}")
                    return

                # 检查文章迁移
                if self.check_article_migration(self.driver):
                    self.log_success("已成功跳转到新链接")
                    # 注意：此时driver已经在新页面上了，继续处理即可

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

                # 如果不是最大深度，创建目录
                if current_depth < self.max_depth:
                    save_dir = os.path.join(parent_dir, page_title)
                    os.makedirs(save_dir, exist_ok=True)
                    self.log_info(f"创建目录: {save_dir}")
                else:
                    # 在最大深度，直接使用父目录
                    save_dir = parent_dir

                # 保存PDF
                if self.save_page_as_pdf(url, save_dir):
                    self.log_success("PDF保存成功")
                else:
                    self.log_error("PDF保存失败")

                # 如果还没到最大深度，继续获取链接
                if current_depth < self.max_depth:
                    self.log_info("开始获取页面链接...")
                    links = self.get_page_links(url)
                    self.log_highlight(f"找到 {len(links)} 个有效链接")

                    for i, link in enumerate(links, 1):
                        self.log_highlight(f"\n处理链接 [{i}/{len(links)}]: {link}")
                        self.crawl_page(link, current_depth + 1, save_dir)
                else:
                    self.log_warning(f"已达到最大深度 {self.max_depth}，停止获取链接")

            except KeyboardInterrupt:
                print("\n\n爬取过程被用户中断...")
                self.stop()
                return
            except Exception as e:
                if self.debug:
                    print(f"处理页面时出错 {url}: {str(e)}")
                    print(traceback.format_exc())
                else:
                    print(f"处理页面时出错: {url}")

        except KeyboardInterrupt:
            print("\n\n爬取过程被用户中断...")
            self.stop()
            return
        except Exception as e:
            if self.debug:
                print(f"处理页面时出错 {url}: {str(e)}")
                print(traceback.format_exc())
            else:
                print(f"处理页面时出错: {url}")

    def process_url(self, url):
        """处理单个起始URL"""
        try:
            print(f"\n开始处理URL: {url}")
            self.driver = self.setup_driver()
            print("浏览器驱动初始化成功")
            self.crawl_page(url)
        except KeyboardInterrupt:
            print("\n\n处理过程被用户中断...")
        except Exception as e:
            if self.debug:
                print(f"处理URL时出错: {url}")
                print(f"错误信息: {str(e)}")
                print(traceback.format_exc())
            else:
                print(f"处理URL失败: {url}")
        finally:
            if self.driver:
                print("正在关闭浏览器驱动...")
                try:
                    self.driver.quit()
                except:
                    pass
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

    def stop(self):
        """停止爬虫"""
        self._stop = True
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def main():
    """主程序入口"""
    try:
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

    except KeyboardInterrupt:
        print("\n\n程序被用户中断，正在清理资源并退出...")
        sys.exit(0)
    except Exception as e:
        if args.debug:
            print(f"程序运行出错: {str(e)}")
            print(traceback.format_exc())
        else:
            print("程序运行出错")
    finally:
        # 确保所有资源都被清理
        for crawler in active_crawlers: # type: ignore
            if crawler.driver:
                crawler.driver.quit()

if __name__ == "__main__":
    main() 