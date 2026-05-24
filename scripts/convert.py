import requests
import re
import os
import datetime

# 配置区域
INPUT_SOURCES = "sources.txt"
OUTPUT_DIR = "dist"

def clean_domain(domain):
    """清理域名：移除不支持的通配符前缀，确保格式合法"""
    if not domain: return None
    # 移除开头的 * 和 . (例如: *-ad-sign.byteimg.com -> ad-sign.byteimg.com)
    domain = re.sub(r'^[\*\.-]+', '', domain)
    # 确保只保留合法的域名字符
    domain = domain.strip().lower()
    if '.' in domain and not domain.endswith('.'):
        return domain
    return None

def extract_domain(line):
    """提取域名：解析 || 语法和纯域名"""
    # 匹配 || 之后到 ^ 或 / 或 结尾之间的内容
    match = re.search(r'\|\|([^/^$^\s]+)', line)
    if match:
        return clean_domain(match.group(1))
    
    # 匹配纯域名格式
    if re.match(r'^[a-z0-9\.\-\*]+\.[a-z]{2,}$', line, re.I):
        return clean_domain(line)
    return None

def process_rules():
    dns_domains = set()  # 使用 set 自动实现简单去重
    regex_rules = set()
    status_report = []
    
    if not os.path.exists(INPUT_SOURCES):
        print(f"[!] {INPUT_SOURCES} 文件不存在")
        return [], [], []

    with open(INPUT_SOURCES, 'r', encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    
    for url in urls:
        try:
            print(f"正在下载: {url}")
            resp = requests.get(url, timeout=20)
            lines = resp.text.splitlines()
            count_before = len(dns_domains)
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith(('!', '#', '[')): continue
                
                # 识别正则规则
                if line.startswith('/^') or (line.startswith('/') and line.endswith('/')):
                    regex_rules.add(line)
                else:
                    # 识别域名规则
                    domain = extract_domain(line)
                    if domain:
                        dns_domains.add(domain)
            
            status_report.append(f"成功: {url} (新增 {len(dns_domains)-count_before} 条)")
        except Exception as e:
            status_report.append(f"失败: {url} (错误: {e})")
            
    # 仅执行简单排序，不执行缩写合并
    final_domains = sorted(list(dns_domains))
    final_regexes = sorted(list(regex_rules))
            
    return final_domains, final_regexes, status_report

def generate_output(domains, regexes, status_report):
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = [
        f"! Title: AdRules List",
        f"! Homepage: https://github.com/Whitisnotme/AdRules-List",
        f"! Update: {now}(GMT+8)",
        f"! Total count: {len(domains) + len(regexes)}",
        f"! ------------------------------------------------------------"
    ]
    
    # 1. 导出 adblock.txt (已修复通配符报错)
    with open(f"{OUTPUT_DIR}/adblock.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(header) + "\n\n")
        f.write("\n".join([f"||{d}^" for d in domains]))
        
    # 2. 导出 domain-suffix.list (专用格式)
    with open(f"{OUTPUT_DIR}/DOMAIN-SUFFIX.list", "w", encoding='utf-8') as f:
        f.write(f"# Update: {now}\n")
        f.write(f"# Total: {len(domains)}\n\n")
        f.write("\n".join([f"domain-suffix,{d}" for d in domains]))
        
    # 3. 导出 advanced_regex.txt
    with open(f"{OUTPUT_DIR}/advanced_regex.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(header) + "\n\n")
        f.write("\n".join(regexes))
        
    # 4. 导出状态日志
    with open(f"{OUTPUT_DIR}/status.log", "w", encoding='utf-8') as f:
        f.write(f"更新时间: {now}\n")
        f.write(f"总计条目: {len(domains) + len(regexes)}\n")
        f.write("-" * 30 + "\n")
        f.write("\n".join(status_report))

if __name__ == "__main__":
    d, r, s = process_rules()
    generate_output(d, r, s)
    print(f"\n任务完成！")
    print(f"生成的域名总数: {len(d)}")
    print(f"生成的正则总数: {len(r)}")