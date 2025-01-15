# WebpageToPDF

A tool for batch downloading and converting WeChat articles to PDF format.


## Usage

1. Create `urls.txt` with article links (one per line)
2. Run
```bash
pip install -r requirements.txt

python main.py [options]
```

### Options
```
-h, --help            Show help
-d num, --depth num   Crawl depth (default: 3)
-t sec, --delay sec   Page load delay (default: 3)
-D, --debug          Enable debug logs
-v, --visible        Show browser window
```

### Examples
```bash
python main.py -d 3                  # Depth: 3
python main.py -t 5                  # Delay: 5s
python main.py -d 2 -t 3 -D         # Depth: 2, Delay: 3s, Debug mode
python main.py -D -v                # Debug mode with browser

# Cleanup
python clean.py -a                  # Remove all generated files
python clean.py -c                  # Clear cache only
```
