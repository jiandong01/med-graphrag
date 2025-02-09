import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any

class IndicationNormalizer:
    """适应症规范化处理器"""
    
    def __init__(self):
        """初始化规范化处理器"""
        # 常见的需要删除的前缀
        self.prefixes_to_remove = [
            r'^\d+\.',
            r'^\d+\)',
            r'^\(\d+\)',
            r'^[①②③④⑤⑥⑦⑧⑨⑩]',
            r'^[•●◆■]'
        ]
        
        # 合并这些前缀为一个正则表达式
        self.prefix_pattern = '|'.join(self.prefixes_to_remove)
    
    def clean_text(self, text: str) -> str:
        """清理文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
            
        # 使用 BeautifulSoup 清理 HTML
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        
        # 删除前缀
        text = re.sub(self.prefix_pattern, '', text)
        
        # 基本清理
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # 合并多个空格
        text = re.sub(r'[,，;；。\n\r]+', '。', text)  # 统一分隔符
        
        return text
    
    def split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子
        
        Args:
            text: 清理后的文本
            
        Returns:
            List[str]: 句子列表
        """
        if not text:
            return []
            
        # 使用句号分割，保留非空句子
        sentences = [s.strip() for s in text.split('。') if s.strip()]
        return sentences
    
    def process_details(self, details: List[Dict[str, str]]) -> Dict[str, Any]:
        """处理详情数据
        
        Args:
            details: 原始详情列表，每个详情包含 tag 和 content
            
        Returns:
            Dict[str, Any]: 处理后的结构化数据
        """
        processed = {
            'indications': [],
            'contraindications': [],
            'precautions': [],
            'populations': []
        }
        
        for detail in details:
            tag = detail.get('tag', '')
            content = detail.get('content', '')
            
            # 清理文本
            cleaned_text = self.clean_text(content)
            if not cleaned_text:
                continue
                
            # 分割成句子
            sentences = self.split_into_sentences(cleaned_text)
            
            # 根据标签分类
            if '适应症' in tag:
                processed['indications'].extend(sentences)
            elif '禁忌' in tag:
                processed['contraindications'].extend(sentences)
            elif '注意事项' in tag:
                processed['precautions'].extend(sentences)
            elif '人群' in tag:
                processed['populations'].extend(sentences)
        
        # 去重
        for key in processed:
            processed[key] = list(set(processed[key]))
        
        return processed
