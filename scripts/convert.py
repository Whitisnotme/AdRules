import requests
import re
import os
import datetime

# 配置区域
INPUT_SOURCES = "sources.txt"
OUTPUT_DIR = "dist"

def extract_domain(line):
    """提取域名：兼容 || 和 纯域名格式"""
    match = re.search(r'(?:\|\|)([^/^$]+)', line)
    if match: return match.group(1)
    if re.match(r'^[a-z0-9.-]+\.[a-z]{2,}$', line): return line
    return None

def process_rules():
    dns_domains = set()
    regex_rules = set()
    status_report = []
    
    if not os.path.exists(INPUT_SOURCES):
        print(f"[!] {INPUT_SOURCES} 文件不存在")
        return [], [], []

    with open(INPUT_SOURCES, 'r') as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    
    for url in urls:
        try:
            resp = requests.get(url, timeout=20)
            lines = resp.text.splitlines()
            count_start = len(dns_domains)
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith(('!', '#', '[')): continue
                
                # 分类处理：正则类 vs 域名类
                if line.startswith('/^'):
                    regex_rules.add(line)
                else:
                    domain = extract_domain(line)
                    if domain: dns_domains.add(domain.lower())
            
            status_report.append(f"成功: {url} (新增 {len(dns_domains)-count_start} 条)")
        except Exception as e:
            status_report.append(f"失败: {url} (错误: {e})")
            
    # 深度去重
    sorted_domains = sorted(list(dns_domains))
    final_domains = []
    for d in sorted_domains:
        if not any(d.endswith('.' + f) for f in final_domains):
            final_domains.append(d)
            
    return final_domains, sorted(list(regex_rules)), status_report

def generate_output(domains, regexes, status_report):
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    header = [
        f"! Title: AdRules List",
        f"! Homepage: https://github.com/Whitisnotme/AdRules-List",
        f"! Update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}(GMT+8)",
        f"! Total count: {len(domains) + len(regexes)}",
        f"! ------------------------------------------------------------"
    ]
    
    # 1. 导出 adblock.txt (纯规则)
    with open(f"{OUTPUT_DIR}/adblock.txt", "w") as f:
        f.write("\n".join(header) + "\n\n")
        f.write("\n".join([f"||{d}^" for d in domains]))
        
    # 2. 导出 advanced_regex.txt (正则规则)
    with open(f"{OUTPUT_DIR}/advanced_regex.txt", "w") as f:
        f.write("\n".join(header) + "\n\n")
        f.write("\n".join(regexes))
        
    # 3. 导出状态日志 (运维监控)
    with open(f"{OUTPUT_DIR}/status.log", "w") as f:
        f.write(f"更新时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总计条目: {len(domains) + len(regexes)}\n")
        f.write("-" * 30 + "\n")
        f.write("\n".join(status_report))

if __name__ == "__main__":
    d, r, s = process_rules()
    generate_output(d, r, s)