import requests
import re
import os
import datetime

# 配置区域
INPUT_SOURCES = "sources.txt"
OUTPUT_DIR = "dist"

def clean_domain(domain):
    """清理域名：移除不支持的通配符前缀，并确保格式合法"""
    if not domain: return None
    domain = re.sub(r'^[\*\.]+', '', domain)
    if '.' in domain and not domain.endswith('.'):
        return domain.lower()
    return None

def extract_domain(line):
    """提取域名：兼容 || 和 纯域名格式"""
    match = re.search(r'\|\|([^/^$\*\s]+)', line)
    if match:
        return clean_domain(match.group(1))
    
    # 匹配纯域名格式
    if re.match(r'^[a-z0-9.-]+\.[a-z]{2,}$', line, re.I):
        return clean_domain(line)
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
                
                # 增强正则分类识别
                if line.startswith('/^') or (line.startswith('/') and line.endswith('/')):
                    regex_rules.add(line)
                elif '*' in line and not line.startswith('||'):
                    pass 
                else:
                    domain = extract_domain(line)
                    if domain: dns_domains.add(domain)
            
            status_report.append(f"成功: {url} (当前总计 {len(dns_domains)} 域名)")
        except Exception as e:
            status_report.append(f"失败: {url} (错误: {e})")
            
    # 深度去重逻辑
    sorted_domains = sorted(list(dns_domains), key=len)
    final_domains = []
    for d in sorted_domains:
        is_subdomain = False
        for f in final_domains:
            if d.endswith('.' + f):
                is_subdomain = True
                break
        if not is_subdomain:
            final_domains.append(d)
            
    return sorted(final_domains), sorted(list(regex_rules)), status_report

def generate_output(domains, regexes, status_report):
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = [
        f"! Title: AdRules List",
        f"! Homepage: https://github.com/Whitisnotme/AdRules-List",
        f"! Update: {now_str}(GMT+8)",
        f"! Total count: {len(domains) + len(regexes)}",
        f"! ------------------------------------------------------------"
    ]
    
    # 1. 导出 adblock.txt
    with open(f"{OUTPUT_DIR}/adblock.txt", "w") as f:
        f.write("\n".join(header) + "\n\n")
        f.write("\n".join([f"||{d}^" for d in domains]))
        
    # 2. 导出 advanced_regex.txt
    with open(f"{OUTPUT_DIR}/advanced_regex.txt", "w") as f:
        f.write("\n".join(header) + "\n\n")
        f.write("\n".join(regexes))
        
    # 3. 导出 domain-suffix.list
    with open(f"{OUTPUT_DIR}/DOMAIN-SUFFIX.list", "w") as f:
        f.write(f"# Update: {now_str}\n")
        f.write(f"# Total: {len(domains)}\n")
        f.write("\n".join([f"domain-suffix,{d}" for d in domains]))
        
    # 4. 导出状态日志
    with open(f"{OUTPUT_DIR}/status.log", "w") as f:
        f.write(f"更新时间: {now_str}\n")
        f.write(f"总计域名: {len(domains)}\n")
        f.write(f"总计正则: {len(regexes)}\n")
        f.write("-" * 30 + "\n")
        f.write("\n".join(status_report))

if __name__ == "__main__":
    d, r, s = process_rules()
    generate_output(d, r, s)
    print("处理完成，请检查 dist 目录")