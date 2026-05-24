import requests
import re
import os
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置
INPUT_SOURCES = "sources.txt"
OUTPUT_DIR = "dist"
TIMEZONE = timezone(timedelta(hours=8))  # 北京时间

def get_session():
    """初始化带有重试机制的会话"""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

def extract_domain(line):
    """提取域名：保持原始格式，不做归并"""
    if line.startswith('||'):
        return line[2:].rstrip('^')
    if re.match(r'^[a-z0-9\.\-\*]+\.[a-z]{2,}$', line, re.I):
        return line
    return None

def fetch_and_parse(url, session):
    """从源下载并解析规则"""
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        domains, regexes = set(), set()
        
        # 逐行处理规则
        for line in (l.strip() for l in resp.text.splitlines()):
            if not line or line.startswith(('!', '#', '[')): continue
            
            # 分离正则规则与域名规则
            if line.startswith(('/^', '/')) and line.endswith('/'):
                regexes.add(line)
            else:
                d = extract_domain(line)
                if d: domains.add(d)
        return domains, regexes, f"成功: {url} ({len(domains)} 条)"
    except Exception as e:
        return set(), set(), f"失败: {url} (错误: {e})"

def process_rules():
    """并行处理所有源并合并结果"""
    if not os.path.exists(INPUT_SOURCES): return [], [], []
    with open(INPUT_SOURCES, 'r', encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    dns_domains, regex_rules, status_report = set(), set(), []
    session = get_session()
    
    # 使用线程池并发下载
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda u: fetch_and_parse(u, session), urls))

    for domains, regexes, status in results:
        dns_domains.update(domains)
        regex_rules.update(regexes)
        status_report.append(status)
    return sorted(list(dns_domains)), sorted(list(regex_rules)), status_report

def generate_output(domains, regexes, status_report):
    """导出格式化后的规则文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    
    with open(f"{OUTPUT_DIR}/adblock.txt", "w", encoding='utf-8') as f:
        f.write(f"! Update: {now}\n" + "\n".join([f"||{d}^" for d in domains]))
    with open(f"{OUTPUT_DIR}/domain-suffix.list", "w", encoding='utf-8') as f:
        f.write(f"# Update: {now}\n" + "\n".join([f"domain-suffix,{d}" for d in domains]))
    with open(f"{OUTPUT_DIR}/advanced_regex.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(regexes))
    with open(f"{OUTPUT_DIR}/status.log", "w", encoding='utf-8') as f:
        f.write(f"更新时间: {now}\n" + "\n".join(status_report))

if __name__ == "__main__":
    d, r, s = process_rules()
    generate_output(d, r, s)