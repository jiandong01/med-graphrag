from typing import Dict, Tuple

class TagPreprocessor:
    def __init__(self):
        # Define tag mappings for normalization
        self.tag_mappings = {
            # 成分相关
            '成份': 'components',
            '成分': 'components',
            '主要成份': 'components',
            '有效成分': 'components',
            
            # 适应症相关
            '适应症': 'indications',
            '适用症': 'indications',
            '适应证': 'indications',
            '功能主治': 'indications',
            
            # 禁忌相关
            '禁忌': 'contraindications',
            '禁忌症': 'contraindications',
            
            # 不良反应相关
            '不良反应': 'adverse_reactions',
            '副作用': 'adverse_reactions',
            
            # 注意事项相关
            '注意事项': 'precautions',
            '警告': 'precautions',
            
            # 相互作用相关
            '药物相互作用': 'interactions',
            '相互作用': 'interactions',
            
            # 用法用量相关
            '用法用量': 'usage',
            '用药方法': 'usage',
            '给药方式': 'usage',
            
            # 批准文号相关
            '批准文号': 'approval_number'
        }
        
        # Define main categories that should be included in the primary mapping
        self.main_categories = {
            'components', 'indications', 'contraindications',
            'adverse_reactions', 'precautions', 'interactions', 'usage',
            'approval_number'
        }
    
    def process_tag(self, original_tag: str) -> Tuple[str, bool]:
        """
        Process a tag and return its normalized form
        
        Args:
            original_tag: The original tag from the database
            
        Returns:
            Tuple[str, bool]: (normalized_tag, is_main_category)
        """
        # Clean the tag
        cleaned_tag = original_tag.strip()
        
        # Get normalized tag
        normalized_tag = self.tag_mappings.get(cleaned_tag, cleaned_tag)
        
        # Check if it's a main category
        is_main = normalized_tag in self.main_categories
        
        return normalized_tag, is_main
    
    def get_mapping_properties(self) -> Dict:
        """
        Get Elasticsearch mapping properties
        
        Returns:
            Dict: Elasticsearch mapping properties for the drug index
        """
        return {
            "details": {
                "type": "nested",
                "properties": {
                    "tag": {"type": "keyword"},
                    "content": {"type": "text"}
                }
            }
        }
