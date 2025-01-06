import os
import shutil
import argparse
from pathlib import Path

def clean_cache():
    """清理浏览器缓存和临时文件"""
    cache_paths = [
        # Chrome缓存目录
        os.path.expanduser('~/.cache/chromium'),
        os.path.expanduser('~/.cache/google-chrome'),
        # ChromeDriver缓存
        os.path.expanduser('~/.wdm'),
        # 其他可能的缓存目录
        './__pycache__',
        './chromedriver_win32',
        './chromedriver_mac64',
        './chromedriver_linux64'
    ]
    
    for path in cache_paths:
        if os.path.exists(path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                print(f"已清理: {path}")
            except Exception as e:
                print(f"清理 {path} 时出错: {e}")

def clean_pdfs():
    """清理生成的PDF文件"""
    pdf_dir = "./pdfs"
    if os.path.exists(pdf_dir):
        try:
            shutil.rmtree(pdf_dir)
            print(f"已清理PDF目录: {pdf_dir}")
        except Exception as e:
            print(f"清理PDF目录时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description='清理工具')
    parser.add_argument('-a', '--all', action='store_true',
                      help='清理所有内容（缓存和PDF）')
    parser.add_argument('-c', '--cache', action='store_true',
                      help='仅清理缓存')
    args = parser.parse_args()

    if not (args.all or args.cache):
        parser.print_help()
        return

    if args.all:
        print("清理所有内容...")
        clean_cache()
        clean_pdfs()
    elif args.cache:
        print("清理缓存...")
        clean_cache()

    print("清理完成！")

if __name__ == "__main__":
    main() 