import os
import re
import requests
import fitz  # PyMuPDF
from urllib.parse import urljoin

# 配置参数
SOURCE_PDF = "W020210624327149500026.pdf"  # PDF文件名
OUTPUT_DIR = "downloaded_pdfs"  # 保存目录
BASE_URL = "https://www.mee.gov.cn/"  # 基础URL（用于拼接相对路径）
KEYWORDS = ["手册", "指南", "规范", "标准", "技术"]  # 目标关键词

os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_links_from_pdf(pdf_path):
    """提取PDF中的超链接（匹配关键词附近链接）"""
    doc = fitz.open(pdf_path)
    links = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text_blocks = page.get_text("words")  # 格式: [(x0,y0,x1,y1, "文字"), ...]
        
        for link in page.get_links():
            if not link.get("uri"):
                continue  # 跳过非URL链接
            
            url = link["uri"]
            link_rect = link["from"]  # fitz.Rect对象
            
            # 扩大搜索范围（提高容错率）
            x0, y0 = link_rect.x0 - 20, link_rect.y0 - 10  # 左上方扩展
            x1, y1 = link_rect.x1 + 50, link_rect.y1 + 20  # 右下方扩展
            
            # 提取链接附近的文本（优化版）
            nearby_text = []
            for block in text_blocks:
                bx0, by0, bx1, by1, text = block[:5]
                if (bx0 >= x0 and bx1 <= x1 and by0 >= y0 and by1 <= y1):
                    nearby_text.append(text)
            link_text = " ".join(nearby_text).strip()
            
            # 调试输出（可选）
            print(f"Page {page_num + 1}: 附近文本 -> '{link_text}' | URL -> {url}")
            
            # 如果附近文本包含关键词则保留
            if any(keyword in link_text for keyword in KEYWORDS):
                links.append({
                    "url": url,
                    "source": link_text if link_text else f"隐藏链接(P{page_num + 1})"
                })

    doc.close()
    return links

def download_pdf(url, save_path, max_retries=3):
    """下载PDF文件（含重试和超时处理）"""
    headers = {"User-Agent": "Mozilla/5.0"}  # 模拟浏览器请求
    try:
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, stream=True, timeout=30)
                response.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ 下载成功: {save_path}")
                return True
            except requests.exceptions.RequestException as e:
                print(f"⚠️ 下载失败 [尝试 {attempt + 1}/{max_retries}]: {url}\n错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 致命错误: {url}\n{e}")
        return False

def main():
    print("=== 开始解析PDF ===")
    links = extract_links_from_pdf(SOURCE_PDF)
    print(f"共找到 {len(links)} 个匹配链接")
    
    for idx, link in enumerate(links, 1):
        url = link["url"]
        if not url.startswith(('http://', 'https://')):
            url = urljoin(BASE_URL, url)  # 拼接完整URL
        
        # 生成合法文件名
        link_text = link["source"]
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', link_text)[:100]  # 限制长度并替换非法字符
        filename = f"{idx:03d}_{safe_name}.pdf" if safe_name else f"file_{idx:03d}.pdf"
        save_path = os.path.join(OUTPUT_DIR, filename)
        
        # 跳过已存在文件
        if os.path.exists(save_path):
            print(f"⏩ 文件已存在: {save_path}")
            continue
            
        print(f"\n下载中 [{idx}/{len(links)}]: {url}")
        download_pdf(url, save_path)

if __name__ == "__main__":
    main()
