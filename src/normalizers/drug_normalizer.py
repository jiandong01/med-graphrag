import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import html

class DrugNormalizer:
    """药品信息规范化处理类"""
    
    def __init__(self):
        """初始化规范化器"""
        # 常见的修饰词，可以根据需要扩展
        self.modifiers = [
            '本品', '药品', '该药', '此药',
            '适用于', '用于', '主要用于', '可用于',
            '能够', '可以', '建议', '推荐'
        ]
    
    def clean_text(self, text: str) -> str:
        """清理文本，移除HTML标签和特殊字符
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
            
        # 解码HTML实体
        text = html.unescape(text)
        
        # 使用BeautifulSoup移除HTML标签
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符，但保留中文、数字、字母、常用标点
        text = re.sub(r'[^\u4e00-\u9fff\w\s,.;:，。；：、]+', '', text)
        
        return text.strip()
    
    def standardize_name(self, name: str) -> str:
        """标准化药品名称"""
        if not name:
            return ""
            
        # 首先清理文本
        name = self.clean_text(name)
        
        # 转换为小写
        name = name.lower()
        
        # 移除修饰词
        for modifier in self.modifiers:
            name = name.replace(modifier, '')
        
        return name.strip()
    
    def standardize_spec(self, spec: str) -> str:
        """标准化规格信息"""
        return self.clean_text(spec)
    
    def normalize_date(self, date_str: str) -> str:
        """标准化日期格式"""
        if not date_str:
            return ""
        try:
            # 首先清理文本
            date_str = self.clean_text(date_str)
            # 解析日期
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return date.strftime('%Y-%m-%d')
        except:
            return date_str.split()[0] if date_str else ""

    def process_components(self, components: List[Dict]) -> List[Dict]:
        """处理药品成分信息
        
        Args:
            components: 原始成分信息列表
            
        Returns:
            List[Dict]: 处理后的成分列表
        """
        processed = []
        for comp in components:
            if not isinstance(comp, dict):
                continue
                
            name = comp.get('name', '').strip()
            content = comp.get('content', '').strip()
            
            if name or content:
                processed.append({
                    'name': self.standardize_name(name),
                    'content': content
                })
        
        return processed
    
    def process_details(self, details: List[Dict]) -> Dict[str, Any]:
        """处理药品详情信息"""
        # 初始化结果字典
        result = {
            'components': [],       # 改为列表，不区分主料和辅料
            'indications': [],      
            'contraindications': [], 
            'adverse_reactions': [], 
            'precautions': [],      
            'interactions': [],      
            'usage': '',
            'approval_number': '',
            'details': []
        }
        
        # 标签到字段的映射
        tag_mapping = {
            'components': 'components',
            '成份': 'components',
            '成分': 'components',
            '主要成份': 'components',
            '有效成分': 'components',
            '辅料': 'components',
            '赋形剂': 'components',
            
            'indications': 'indications',
            '适应症': 'indications',
            '适用症': 'indications',
            '适应证': 'indications',
            '功能主治': 'indications',
            
            'contraindications': 'contraindications',
            '禁忌': 'contraindications',
            '禁忌症': 'contraindications',
            
            'adverse_reactions': 'adverse_reactions',
            '不良反应': 'adverse_reactions',
            '副作用': 'adverse_reactions',
            
            'precautions': 'precautions',
            '注意事项': 'precautions',
            '警告': 'precautions',
            
            'interactions': 'interactions',
            '药物相互作用': 'interactions',
            '相互作用': 'interactions',
            
            'usage': 'usage',
            '用法用量': 'usage',
            '用药方法': 'usage',
            '给药方式': 'usage',
            
            'approval_number': 'approval_number',
            '批准文号': 'approval_number'
        }
        
        def clean_component(text: str) -> str:
            """清理成分文本"""
            text = self.clean_text(text)
            # 移除常见前缀
            text = re.sub(r'^(本品|药品|该药)(每片|每粒|每袋|每支)?含', '', text)
            # 移除常见说明词
            text = re.sub(r'(组成|成分|配料)[:：]?', '', text)
            return text.strip()
        
        def process_components(content: str) -> None:
            """处理成分内容，保持语义完整性"""
            # 清理HTML和特殊字符
            content = self.clean_text(content)
            
            # 按句号、分号分割
            items = re.split(r'[。；;]', content)
            
            # 清理每个成分描述
            for item in items:
                item = item.strip()
                if not item:
                    continue
                
                # 移除常见前缀
                item = re.sub(r'^(本品|药品|该药)(每片|每粒|每袋|每支)?含', '', item)
                # 移除常见说明词
                item = re.sub(r'^(组成|成分|配料|辅料|主要成分|赋形剂)(为|包括|含有)?[:：]?', '', item)
                # 如果以逗号结尾，去掉
                item = re.sub(r'[,，、]$', '', item)
                
                if item.strip():
                    result['components'].append(item.strip())
        
        def process_text_field(content: str) -> List[str]:
            """处理文本字段，保持语义完整性
            
            Args:
                content: 原始文本内容
                
            Returns:
                List[str]: 处理后的文本列表
            """
            # 清理HTML和特殊字符
            content = self.clean_text(content)
            
            # 按句号、分号分割，这些标点通常表示完整的语义单元
            items = re.split(r'[。；;]', content)
            
            # 清理每个片段，保持内部的逗号等标点
            cleaned_items = []
            for item in items:
                item = item.strip()
                if item:
                    # 如果以逗号结尾，去掉
                    item = re.sub(r'[,，、]$', '', item)
                    cleaned_items.append(item)
            
            return cleaned_items
        
        for detail in details:
            if not isinstance(detail, dict):
                continue
                
            tag = detail.get('tag', '').strip()
            content = detail.get('content', '').strip()
            
            if not tag or not content:
                continue
            
            # 保存原始详情
            result['details'].append({
                'tag': tag,
                'content': content  # 保持原始内容
            })
            
            # 处理特定字段
            field = tag_mapping.get(tag)
            if field:
                if field == 'components':
                    process_components(content)
                elif field in ['indications', 'contraindications', 
                             'adverse_reactions', 'precautions', 'interactions']:
                    # 处理文本字段，保持语义完整性
                    items = process_text_field(content)
                    # 直接扩展列表，保持顺序
                    result[field].extend(items)
                else:
                    # 其他字段直接使用清理后的内容
                    result[field] = self.clean_text(content)
        
        # 对所有列表字段去重，但保持顺序
        for field in ['components', 'indications', 'contraindications', 
                     'adverse_reactions', 'precautions', 'interactions']:
            # 使用dict.fromkeys保持顺序的同时去重
            result[field] = list(dict.fromkeys(result[field]))
        
        return result
