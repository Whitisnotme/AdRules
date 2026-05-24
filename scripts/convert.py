import requests
import re
import os
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置区域
INPUT_SOURCES = "sources.txt"
OUTPUT_DIR = "dist"
TIMEZONE = timezone(timedelta(hours=8))  # 强制使用北京时间

def get_session():
    """初始化带重试机制的请求会话"""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

def extract_domain(line):
    """提取规则中的域名，保留上游定义的原始格式"""
    if line.startswith('||'):
        return line[2:].rstrip('^')
    if re.match(r'^[a-z0-9\.\-\*]+\.[a-z]{2,}$', line, re.I):
        return line
    return None

def fetch_and_parse(url, session):
    """下载并按分类解析规则"""
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        domains, regexes = set(), set()
        
        for line in (l.strip() for l in resp.text.splitlines()):
            if not line or line.startswith(('!', '#', '[')): continue
            
            # 区分正则规则与域名规则
            if line.startswith(('/^', '/')) and line.endswith('/'):
                regexes.add(line)
            else:
                d = extract_domain(line)
                if d: domains.add(d)
        return domains, regexes, f"成功: {url} ({len(domains)} 条)"
    except Exception as e:
        return set(), set(), f"失败: {url} (错误: {e})"

def process_rules():
    """并行处理所有源，合并去重"""
    if not os.path.exists(INPUT_SOURCES): return [], [], []
    with open(INPUT_SOURCES, 'r', encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    dns_domains, regex_rules, status_report = set(), set(), []
    session = get_session()
    
    # 线程池并发下载
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda u: fetch_and_parse(u, session), urls))

    for domains, regexes, status in results:
        dns_domains.update(domains)
        regex_rules.update(regexes)
        status_report.append(status)
    return sorted(list(dns_domains)), sorted(list(regex_rules)), status_report

def generate_output(domains, regexes, status_report):
    """生成并导出标准格式规则文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    
    # 统一头部格式
    header_info = (
        f"! Title: AdRules List\n"
        f"! Homepage: https://github.com/Whitisnotme/AdRules\n"
        f"! Update: {now}(GMT+8)\n"
        f"! Total count: {len(domains) + len(regexes)}\n"
        f"! ------------------------------------------------------------\n\n"
    )
    
    # DOMAIN-SUFFIX 格式专用注释头部
    clash_header = header_info.replace("!", "#")

    # 导出文件
    with open(f"{OUTPUT_DIR}/adblock.txt", "w", encoding='utf-8') as f:
        f.write(header_info + "\n".join([f"||{d}^" for d in domains]))
        
    with open(f"{OUTPUT_DIR}/domain-suffix.list", "w", encoding='utf-8') as f:
        f.write(clash_header + "\n".join([f"domain-suffix,{d}" for d in domains]))
        
    with open(f"{OUTPUT_DIR}/advanced_regex.txt", "w", encoding='utf-8') as f:
        f.write(header_info + "\n".join(regexes))
        
    with open(f"{OUTPUT_DIR}/status.log", "w", encoding='utf-8') as f:
        f.write(f"更新时间: {now}\n总计条目: {len(domains) + len(regexes)}\n" + "-"*30 + "\n" + "\n".join(status_report))

if __name__ == "__main__":
    d, r, s = process_rules()
    generate_output(d, r, s)