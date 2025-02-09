import re
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import csv
from pathlib import Path

class IndicationNormalizer:
    """适应症规范化处理类"""
    
    def __init__(self):
        # 分隔符模式
        self.split_pattern = r'[,;，；、]|\s+(?:和|及|与|or|and)\s+'
        
        # 常见的修饰词，这些词会被移除
        self.modifiers = {
            '轻度', '中度', '重度', '急性', '慢性', '早期', '晚期',
            '初期', '中期', '晚期', '临床', '症状', '表现',
            '伴有', '引起的', '所致', '导致的', '相关的'
        }
        
        # 疾病类别映射
        self.disease_categories = {
            '感染性疾病': {'感染', '病毒', '细菌', '真菌', '寄生虫'},
            '心血管疾病': {'心脏', '血管', '高血压', '心律失常'},
            '呼吸系统疾病': {'呼吸', '肺', '气管', '支气管'},
            '消化系统疾病': {'胃', '肠', '肝', '胆', '消化'},
            '神经系统疾病': {'神经', '头痛', '癫痫', '麻痹'},
            '内分泌疾病': {'糖尿病', '甲状腺', '激素'},
            '肌肉骨骼疾病': {'关节', '骨', '肌肉', '腱'},
            '皮肤疾病': {'皮肤', '瘙痒', '湿疹'},
            '精神疾病': {'抑郁', '焦虑', '失眠', '精神'},
            '肿瘤': {'癌', '瘤', '恶性', '肿瘤'},
            '其他': set()  # 默认类别
        }
    
    def split_indications(self, text: str) -> List[str]:
        """分割适应症文本为单独的适应症列表
        
        Args:
            text: 原始适应症文本
            
        Returns:
            List[str]: 分割后的适应症列表
        """
        if not text:
            return []
            
        # 使用正则表达式分割
        parts = re.split(self.split_pattern, text)
        
        # 清理并过滤空字符串
        return [part.strip() for part in parts if part.strip()]
    
    def standardize_name(self, name: str) -> str:
        """标准化适应症名称
        
        Args:
            name: 原始适应症名称
            
        Returns:
            str: 标准化后的名称
        """
        if not name:
            return ""
            
        # 转换为小写并移除空白字符
        std_name = name.lower().strip()
        
        # 清理 HTML 实体和特殊字符
        std_name = re.sub(r'&[a-zA-Z]+;', '', std_name)  # 移除 HTML 实体如 &nbsp;
        std_name = re.sub(r'[^\w\s\u4e00-\u9fff]+', ' ', std_name)  # 只保留文字、数字、空格和中文字符
        
        # 移除修饰词
        for modifier in self.modifiers:
            std_name = std_name.replace(modifier, '')
        
        # 移除括号内容
        std_name = re.sub(r'\([^)]*\)', '', std_name)
        
        # 清理多余的空白字符
        std_name = re.sub(r'\s+', ' ', std_name).strip()
        
        return std_name if std_name else ""  # 如果清理后为空，返回空字符串
    
    def get_category(self, indication: str) -> str:
        """获取适应症所属的疾病类别
        
        Args:
            indication: 适应症名称
            
        Returns:
            str: 疾病类别
        """
        for category, keywords in self.disease_categories.items():
            if any(keyword in indication for keyword in keywords):
                return category
        return '其他'
    
    def group_by_category(self, indications: List[str]) -> Dict[str, List[str]]:
        """将适应症按疾病类别分组
        
        Args:
            indications: 适应症列表
            
        Returns:
            Dict[str, List[str]]: 按类别分组的适应症
        """
        groups = defaultdict(list)
        for ind in indications:
            category = self.get_category(ind)
            groups[category].append(ind)
        return dict(groups)
    
    def analyze_indications(self, texts: List[str]) -> Dict:
        """分析适应症文本列表
        
        Args:
            texts: 适应症文本列表
            
        Returns:
            Dict: 分析结果，包含：
                - total: 总适应症数
                - total_unique: 唯一适应症数
                - categories: 各类别的适应症
                - standardization_map: 标准化映射关系
        """
        all_indications = []
        std_to_orig = defaultdict(set)
        
        # 处理所有文本
        for text in texts:
            indications = self.split_indications(text)
            for ind in indications:
                std_name = self.standardize_name(ind)
                all_indications.append(std_name)
                std_to_orig[std_name].add(ind)
        
        # 获取唯一适应症
        unique_indications = list(set(all_indications))
        
        # 按类别分组
        categorized = self.group_by_category(unique_indications)
        
        # 构建分析结果
        analysis = {
            'total': len(all_indications),
            'total_unique': len(unique_indications),
            'categories': categorized,
            'standardization_map': {
                std: list(orig) for std, orig in std_to_orig.items()
            }
        }
        
        return analysis
        
    def value_count(self, texts: List[str], sort_by: str = 'count', ascending: bool = False) -> Dict:
        """统计规范化后的适应症频次
        
        Args:
            texts: 适应症文本列表
            sort_by: 排序依据，可选 'count'（频次）或 'name'（名称）
            ascending: 是否升序排序
            
        Returns:
            Dict: {
                'statistics': {
                    'total_mentions': int,  # 所有提及的总次数
                    'unique_mentions': int,  # 唯一适应症数量
                    'top_categories': List[Tuple],  # 按频次排序的疾病类别
                },
                'counts': {
                    'standard_name': {
                        'count': int,  # 出现次数
                        'original_names': List[str],  # 原始名称列表
                        'category': str,  # 所属类别
                    }
                }
            }
        """
        # 初始化计数器
        counts = defaultdict(lambda: {'count': 0, 'original_names': set(), 'category': None})
        total_mentions = 0
        
        # 遍历所有文本
        for text in texts:
            # 分割并标准化每个适应症
            indications = self.split_indications(text)
            for ind in indications:
                total_mentions += 1
                std_name = self.standardize_name(ind)
                counts[std_name]['count'] += 1
                counts[std_name]['original_names'].add(ind)
        
        # 确定每个适应症的类别
        categorized = self.group_by_category(list(counts.keys()))
        for category, items in categorized.items():
            for item in items:
                counts[item]['category'] = category
        
        # 计算每个类别的总频次
        category_counts = defaultdict(int)
        for std_name, info in counts.items():
            category_counts[info['category']] += info['count']
        
        # 转换 set 为 list，以便 JSON 序列化
        for info in counts.values():
            info['original_names'] = list(info['original_names'])
        
        # 根据排序参数对结果进行排序
        if sort_by == 'count':
            sorted_items = sorted(
                counts.items(),
                key=lambda x: (x[1]['count'], x[0]),  # 按频次排序，频次相同则按名称排序
                reverse=not ascending
            )
        else:  # sort_by == 'name'
            sorted_items = sorted(
                counts.items(),
                key=lambda x: x[0],  # 按名称排序
                reverse=not ascending
            )
        
        # 按类别频次排序
        sorted_categories = sorted(
            category_counts.items(),
            key=lambda x: (x[1], x[0]),  # 按频次排序，频次相同则按类别名称排序
            reverse=True
        )
        
        # 构建返回结果
        result = {
            'statistics': {
                'total_mentions': total_mentions,
                'unique_mentions': len(counts),
                'top_categories': [
                    {
                        'category': cat,
                        'count': count,
                        'percentage': round(count / total_mentions * 100, 2)
                    }
                    for cat, count in sorted_categories
                ]
            },
            'counts': dict(sorted_items)
        }
        
        return result
    
    def export_value_counts(self, texts: List[str], output_file: str,
                          sort_by: str = 'count', ascending: bool = False) -> None:
        """将适应症频次统计导出为 CSV 文件
        
        Args:
            texts: 适应症文本列表
            output_file: 输出文件路径
            sort_by: 排序依据，可选 'count'（频次）或 'name'（名称）
            ascending: 是否升序排序
        """
        # 获取统计结果
        result = self.value_count(texts, sort_by=sort_by, ascending=ascending)
        
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入 CSV 文件
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # 写入头部
            writer.writerow(['标准名称', '频次', '类别', '原始名称'])
            
            # 写入数据
            for name, info in result['counts'].items():
                writer.writerow([
                    name,
                    info['count'],
                    info['category'],
                    '|'.join(info['original_names']) if info['original_names'] else name
                ])
            
            # 写入统计摘要
            writer.writerow([])
            writer.writerow(['统计摘要'])
            writer.writerow(['总提及次数', result['statistics']['total_mentions']])
            writer.writerow(['唯一适应症数', result['statistics']['unique_mentions']])
            writer.writerow([])
            
            # 写入类别统计
            writer.writerow(['疾病类别统计'])
            writer.writerow(['类别', '数量', '占比(%)'])
            for cat_info in result['statistics']['top_categories']:
                writer.writerow([
                    cat_info['category'],
                    cat_info['count'],
                    cat_info['percentage']
                ])
    
    def print_value_counts(self, texts: List[str], top_n: Optional[int] = None,
                          show_details: bool = False) -> None:
        """打印适应症频次统计
        
        Args:
            texts: 适应症文本列表
            top_n: 显示前 N 个结果，None 表示显示所有
            show_details: 是否显示详细信息（原始名称）
        """
        result = self.value_count(texts, sort_by='count', ascending=False)
        stats = result['statistics']
        counts = result['counts']
        
        # 打印总体统计
        print("\n=== 适应症统计摘要 ===")
        print(f"总提及次数: {stats['total_mentions']}")
        print(f"唯一适应症数: {stats['unique_mentions']}")
        
        # 打印类别统计
        print("\n=== 疾病类别统计 ===")
        for cat_info in stats['top_categories']:
            print(f"{cat_info['category']}: {cat_info['count']} ({cat_info['percentage']}%)")
        
        # 打印适应症频次
        print("\n=== 适应症频次统计 ===")
        for i, (name, info) in enumerate(counts.items(), 1):
            if top_n and i > top_n:
                break
                
            print(f"\n{i}. {name}")
            print(f"   频次: {info['count']}")
            print(f"   类别: {info['category']}")
            
            if show_details and info['original_names']:
                print("   原始名称:")
                for orig in info['original_names']:
                    if orig != name:
                        print(f"    - {orig}")
