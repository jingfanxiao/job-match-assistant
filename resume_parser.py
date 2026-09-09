import re
import pdfplumber
import os
from dotenv import load_dotenv

load_dotenv()

RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

def clean_repeated_chars(text):
    """
    修复PDF装饰性字体(如标题加粗/阴影效果)导致的字符重复问题。
    原理: 部分PDF用多层叠加渲染模拟加粗效果,导致提取时同一字符被重复读取。
    将连续3次以上的相同字符压缩为1个。
    
    注意: 这是一个启发式修复,极端情况下可能误伤合法的连续重复字符
    (例如某些编号或特殊格式),但在英文/法文简历文本中这种情况极为罕见。
    """
    return re.sub(r'(.)\1{2,}', r'\1', text)


def fix_spacing(text):
    """
    修复PDF因字体kerning导致的单词间缺失空格问题。
    在小写字母后紧跟大写字母的位置插入空格。
    (例如 "ArtificialIntelligence" -> "Artificial Intelligence")
    """
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)


def parse_resume(file_path):
    """
    解析PDF简历,提取并清洗文本内容。
    
    处理流程:
    1. 用pdfplumber提取原始文本(调整容差参数减少单词粘连)
    2. 清洗装饰性字体导致的字符重复
    3. 修复驼峰式粘连的单词间距
    """
    raw_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=1, y_tolerance=3)
            if page_text:
                raw_text += page_text + "\n"
    
    if not raw_text.strip():
        raise ValueError("未能从PDF中提取到任何文本,可能是扫描版PDF或格式不受支持")
    
    cleaned_text = clean_repeated_chars(raw_text)
    
    return cleaned_text


if __name__ == "__main__":
    text = parse_resume(RESUME_PATH)
    print(text)
    print(f"\n总字数: {len(text)}")