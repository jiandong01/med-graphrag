"""规则分析模块"""

from typing import Dict, List

class RuleAnalyzer:
    def __init__(self):
        # 初始化同义词库、上下位概念库等
        self.synonym_db = {}  # TODO: 这里应该连接到实际的同义词数据库
        self.hierarchy_db = {}  # TODO: 这里应该连接到实际的疾病层级数据库

    def analyze(self, drug_info: Dict, disease_info: Dict) -> Dict:
        """
        执行规则分析
        
        Args:
            drug_info (Dict): 药品信息
            disease_info (Dict): 疾病信息
        
        Returns:
            Dict: 规则分析结果
        """
        result = {
            "is_offlabel": True,
            "confidence": 0.0,
            "reasoning": [],
            "evidence": []
        }

        # 检查输入数据的有效性
        if not drug_info or not disease_info:
            result["reasoning"].append("输入数据不完整")
            return result

        # 执行各种匹配
        exact_match = self.exact_match(drug_info, disease_info)
        synonym_match = self.synonym_match(drug_info, disease_info)
        hierarchy_match = self.hierarchy_match(drug_info, disease_info)
        contraindication_check = self.check_contraindications(drug_info, disease_info)

        # 综合分析结果
        if exact_match:
            result["is_offlabel"] = False
            result["confidence"] = 1.0
            result["reasoning"].append("疾病名称与药品适应症精确匹配")
            result["evidence"].append(f"适应症: {exact_match}")
        elif synonym_match:
            result["is_offlabel"] = False
            result["confidence"] = 0.9
            result["reasoning"].append("疾病名称与药品适应症同义词匹配")
            result["evidence"].append(f"同义词匹配: {synonym_match}")
        elif hierarchy_match:
            result["is_offlabel"] = False
            result["confidence"] = 0.8
            result["reasoning"].append("疾病名称与药品适应症存在上下位关系")
            result["evidence"].append(f"层级关系: {hierarchy_match}")

        if contraindication_check:
            result["is_offlabel"] = True
            result["confidence"] = max(result["confidence"], 0.95)
            result["reasoning"].append("用药违反禁忌症规则")
            result["evidence"].extend(contraindication_check)

        return result

    def exact_match(self, drug_info: Dict, disease_info: Dict) -> str:
        """精确匹配检查"""
        disease_name = disease_info.get("name", "")
        if not disease_name:
            return ""
        disease_name = disease_name.lower()
        for indication in drug_info.get("indications", []):
            if disease_name == indication.lower():
                return indication
        return ""

    def synonym_match(self, drug_info: Dict, disease_info: Dict) -> str:
        """同义词匹配检查"""
        disease_name = disease_info.get("name", "")
        if not disease_name:
            return ""
        disease_name = disease_name.lower()
        disease_synonyms = self.synonym_db.get(disease_name, [])
        for indication in drug_info.get("indications", []):
            if indication.lower() in disease_synonyms:
                return indication
        return ""

    def hierarchy_match(self, drug_info: Dict, disease_info: Dict) -> str:
        """上下位概念匹配检查"""
        disease_name = disease_info.get("name", "")
        if not disease_name:
            return ""
        disease_name = disease_name.lower()
        disease_hierarchy = self.hierarchy_db.get(disease_name, [])
        for indication in drug_info.get("indications", []):
            if indication.lower() in disease_hierarchy:
                return indication
        return ""

    def check_contraindications(self, drug_info: Dict, disease_info: Dict) -> List[str]:
        """禁忌症检查"""
        contraindications = []
        disease_name = disease_info.get("name", "")
        if not disease_name:
            return contraindications
        disease_name = disease_name.lower()
        for contraindication in drug_info.get("contraindications", []):
            if contraindication.lower() in disease_name:
                contraindications.append(contraindication)
        return contraindications
