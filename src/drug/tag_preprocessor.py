import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TagPreprocessor:
    """标签预处理器"""
    
    def __init__(self):
        """初始化标签预处理器"""
        # 标签替换规则
        self.replace_rules = {
            r'\s+': ' ',  # 合并多个空格
            r'[,.，。、]': ' ',  # 替换标点为空格
            r'\(.*?\)': '',  # 移除括号及其内容
            r'［.*?］': '',  # 移除中文方括号及其内容
            r'\[.*?\]': '',  # 移除英文方括号及其内容
        }
        
        # 标签分割模式
        self.split_pattern = r'[;；]\s*'
        
        # 标签过滤规则
        self.filter_rules = [
            lambda x: len(x) >= 2,  # 标签长度至少为2
            lambda x: not x.isdigit(),  # 不是纯数字
            lambda x: not re.match(r'^[a-zA-Z0-9]+$', x),  # 不是纯英文或数字
        ]
    
    def clean_tag(self, tag: str) -> str:
        """清理单个标签
        
        Args:
            tag: 原始标签
            
        Returns:
            str: 清理后的标签
        """
        # 去除首尾空白
        tag = tag.strip()
        
        # 应用替换规则
        for pattern, repl in self.replace_rules.items():
            tag = re.sub(pattern, repl, tag)
        
        return tag.strip()
    
    def filter_tag(self, tag: str) -> bool:
        """过滤标签
        
        Args:
            tag: 待过滤的标签
            
        Returns:
            bool: 是否保留该标签
        """
        return all(rule(tag) for rule in self.filter_rules)
    
    def process_tags(self, tags: List[str]) -> List[str]:
        """处理标签列表
        
        Args:
            tags: 原始标签列表
            
        Returns:
            List[str]: 处理后的标签列表
        """
        processed_tags = set()
        
        for tag in tags:
            # 分割复合标签
            sub_tags = re.split(self.split_pattern, tag)
            
            # 处理每个子标签
            for sub_tag in sub_tags:
                # 清理标签
                cleaned_tag = self.clean_tag(sub_tag)
                
                # 过滤标签
                if cleaned_tag and self.filter_tag(cleaned_tag):
                    processed_tags.add(cleaned_tag)
        
        return list(processed_tags)
    
    def process_drug_data(self, drug_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理药品数据中的标签
        
        Args:
            drug_data: 药品数据
            
        Returns:
            Dict[str, Any]: 处理后的药品数据
        """
        # 获取原始标签
        tags = drug_data.get('tags', [])
        if not tags:
            return drug_data
        
        # 处理标签
        processed_tags = self.process_tags(tags)
        
        # 更新药品数据
        drug_data['tags'] = processed_tags
        
        return drug_data
