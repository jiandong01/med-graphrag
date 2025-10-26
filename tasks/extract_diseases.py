"""
疾病提取任务脚本
支持分批处理、进度跟踪和断点续传

使用方法:
    python tasks/extract_diseases.py --batch-size 100 --start-from 0
    python tasks/extract_diseases.py --resume  # 从上次中断处继续
"""

import os
import sys
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from tqdm import tqdm
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from elasticsearch import Elasticsearch
from app.src.utils import get_elastic_client, setup_logging, load_env

# 加载环境变量
load_env()

# 配置日志
logger = setup_logging("disease_extraction", log_dir="tasks/logs")


class DiseaseExtractionTask:
    """疾病提取任务"""
    
    def __init__(
        self,
        batch_size: int = 100,
        output_dir: str = "tasks/output/diseases",
        state_file: str = "tasks/state/extraction_state.json"
    ):
        """初始化
        
        Args:
            batch_size: 每批处理的药品数量
            output_dir: 输出目录
            state_file: 状态文件路径
        """
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.state_file = Path(state_file)
        
        # 创建必要的目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化 Elasticsearch
        self.es = get_elastic_client()
        self.drugs_index = 'drugs'
        
        # 初始化 DeepSeek API 客户端（延迟初始化，仅在需要时）
        self.client = None
        self.model = "deepseek-chat"  # DeepSeek 官方 API 模型
        
        # 加载或初始化状态
        self.state = self._load_state()
    
    def _init_openai_client(self):
        """初始化 DeepSeek API 客户端"""
        if self.client is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError(
                    "未配置 DEEPSEEK_API_KEY 环境变量。\n"
                    "请在 .env 文件中添加: DEEPSEEK_API_KEY=your_key"
                )
            self.client = OpenAI(
                base_url="https://api.deepseek.com",
                api_key=api_key
            )
            logger.info("DeepSeek API 客户端初始化成功")
        
    def _load_state(self) -> Dict[str, Any]:
        """加载任务状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"加载已有状态: 已处理 {state['processed_count']} 个药品")
                return state
        else:
            return {
                'start_time': datetime.now().isoformat(),
                'processed_count': 0,
                'total_count': 0,
                'processed_drug_ids': [],
                'current_batch': 0,
                'success_count': 0,
                'failure_count': 0,
                'last_updated': datetime.now().isoformat()
            }
    
    def _save_state(self):
        """保存任务状态"""
        self.state['last_updated'] = datetime.now().isoformat()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _generate_stable_id(self, text: str) -> str:
        """生成稳定的ID"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return text_hash[:32]
    
    def get_total_drugs_count(self) -> int:
        """获取需要处理的药品总数"""
        result = self.es.count(
            index=self.drugs_index,
            body={
                "query": {
                    "exists": {
                        "field": "indications"
                    }
                }
            }
        )
        return result['count']
    
    def fetch_batch(self, from_index: int) -> List[Dict[str, Any]]:
        """获取一批药品数据
        
        Args:
            from_index: 起始索引
            
        Returns:
            List[Dict]: 药品数据列表
        """
        query = {
            "size": self.batch_size,
            "from": from_index,
            "_source": ["id", "name", "indications"],
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "indications"}}
                    ],
                    "must_not": [
                        {"ids": {"values": self.state['processed_drug_ids']}}
                    ]
                }
            }
        }
        
        result = self.es.search(index=self.drugs_index, body=query)
        drugs = [hit['_source'] for hit in result['hits']['hits']]
        return drugs
    
    def extract_diseases_from_indication(
        self,
        indication_text: str,
        drug_id: str,
        drug_name: str
    ) -> Optional[Dict[str, Any]]:
        """从适应症文本提取疾病信息
        
        Args:
            indication_text: 适应症文本
            drug_id: 药品ID
            drug_name: 药品名称
            
        Returns:
            Optional[Dict]: 提取结果
        """
        try:
            prompt = f"""请从以下适应症文本中提取疾病信息，包括主要疾病、子疾病和相关疾病。

适应症文本: {indication_text}

请严格按照以下JSON格式返回，不要添加任何其他内容:
{{
  "diseases": [
    {{
      "name": "疾病名称",
      "type": "disease",
      "sub_diseases": [],
      "related_diseases": [
        {{
          "name": "相关疾病或病因",
          "attributes": {{}},
          "relationship": "cause/complication/symptom"
        }}
      ],
      "confidence_score": 0.95
    }}
  ]
}}

注意:
1. 只提取明确的疾病名称，排除症状和治疗效果描述
2. confidence_score 范围 0.0-1.0
3. relationship 可选值: cause(病因), complication(并发症), symptom(症状)
4. 如果没有子疾病或相关疾病，使用空列表[]
"""
            
            # 调用 LLM
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Medical GraphRAG",
                },
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个医学文本分析专家，专门从适应症文本中提取疾病信息。只返回JSON格式的结果，不要添加任何解释。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            response = completion.choices[0].message.content
            
            # 提取 JSON
            json_str = response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            
            # 清理可能的控制字符
            json_str = ''.join(char for char in json_str if char >= ' ' or char in ['\n', '\r', '\t'])
            
            # 解析 JSON
            result = json.loads(json_str)
            
            # 添加元数据
            return {
                'id': self._generate_stable_id(indication_text),
                'drug_id': drug_id,
                'drug_name': drug_name,
                'indication_text': indication_text,
                'diseases': result.get('diseases', []),
                'extraction_time': datetime.now().isoformat(),
                'confidence': 0.95
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 [{drug_name}]: {str(e)}")
            logger.error(f"原始响应: {response[:200]}...")
            return None
        except Exception as e:
            logger.error(f"提取失败 [{drug_name}]: {str(e)}")
            return None
    
    def process_batch(self, batch_drugs: List[Dict], batch_number: int) -> Dict[str, Any]:
        """处理一批药品
        
        Args:
            batch_drugs: 药品列表
            batch_number: 批次号
            
        Returns:
            Dict: 批次处理结果
        """
        batch_results = {
            'batch_number': batch_number,
            'start_time': datetime.now().isoformat(),
            'drugs_count': len(batch_drugs),
            'extractions': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        # 处理每个药品
        for drug in tqdm(batch_drugs, desc=f"批次 {batch_number}", leave=False):
            drug_id = drug['id']
            drug_name = drug['name']
            indications = drug.get('indications', [])
            
            # 确保是列表
            if isinstance(indications, str):
                indications = [indications]
            
            # 处理每条适应症
            for indication in indications:
                if not indication or not indication.strip():
                    continue
                
                # 提取疾病
                result = self.extract_diseases_from_indication(
                    indication,
                    drug_id,
                    drug_name
                )
                
                if result:
                    batch_results['extractions'].append(result)
                    batch_results['success_count'] += 1
                else:
                    batch_results['failure_count'] += 1
                
                # 添加小延迟避免API限流
                time.sleep(0.1)
            
            # 更新已处理的药品ID
            if drug_id not in self.state['processed_drug_ids']:
                self.state['processed_drug_ids'].append(drug_id)
            self.state['processed_count'] += 1
        
        batch_results['end_time'] = datetime.now().isoformat()
        return batch_results
    
    def save_batch_results(self, batch_results: Dict[str, Any]):
        """保存批次结果
        
        Args:
            batch_results: 批次结果
        """
        # 保存提取结果
        batch_file = self.output_dir / f"batch_{batch_results['batch_number']:05d}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"批次 {batch_results['batch_number']} 结果已保存: {batch_file}")
        logger.info(f"  - 成功: {batch_results['success_count']}")
        logger.info(f"  - 失败: {batch_results['failure_count']}")
    
    def run(self, start_from: Optional[int] = None):
        """运行任务
        
        Args:
            start_from: 从哪个批次开始（None表示继续上次）
        """
        # 初始化 OpenAI 客户端
        self._init_openai_client()
        
        # 获取总数
        if self.state['total_count'] == 0:
            total_count = self.get_total_drugs_count()
            self.state['total_count'] = total_count
            logger.info(f"需要处理的药品总数: {total_count}")
        else:
            total_count = self.state['total_count']
        
        # 确定起始位置
        if start_from is not None:
            current_index = start_from * self.batch_size
            current_batch = start_from
        else:
            current_index = self.state['processed_count']
            current_batch = self.state['current_batch']
        
        logger.info(f"开始处理...")
        logger.info(f"  - 起始索引: {current_index}")
        logger.info(f"  - 起始批次: {current_batch}")
        logger.info(f"  - 已处理: {self.state['processed_count']}/{total_count}")
        logger.info(f"  - 批次大小: {self.batch_size}")
        
        # 计算总批次数
        total_batches = (total_count + self.batch_size - 1) // self.batch_size
        
        # 主循环
        try:
            with tqdm(
                total=total_count,
                initial=self.state['processed_count'],
                desc="总进度",
                unit="药品"
            ) as pbar:
                
                while current_index < total_count:
                    # 获取一批数据
                    batch_drugs = self.fetch_batch(current_index)
                    
                    if not batch_drugs:
                        logger.info("没有更多数据，任务完成")
                        break
                    
                    # 处理批次
                    logger.info(f"\n{'='*60}")
                    logger.info(f"处理批次 {current_batch + 1}/{total_batches}")
                    logger.info(f"药品索引: {current_index} - {current_index + len(batch_drugs)}")
                    logger.info(f"{'='*60}")
                    
                    batch_results = self.process_batch(batch_drugs, current_batch)
                    
                    # 保存批次结果
                    self.save_batch_results(batch_results)
                    
                    # 更新状态
                    self.state['current_batch'] = current_batch + 1
                    self.state['success_count'] += batch_results['success_count']
                    self.state['failure_count'] += batch_results['failure_count']
                    self._save_state()
                    
                    # 更新进度
                    pbar.update(len(batch_drugs))
                    
                    # 移动到下一批
                    current_index += self.batch_size
                    current_batch += 1
                    
                    # 显示统计信息
                    logger.info(f"\n当前统计:")
                    logger.info(f"  - 已处理药品: {self.state['processed_count']}/{total_count}")
                    logger.info(f"  - 已完成批次: {current_batch}/{total_batches}")
                    logger.info(f"  - 成功提取: {self.state['success_count']}")
                    logger.info(f"  - 失败次数: {self.state['failure_count']}")
                    logger.info(f"  - 成功率: {self.state['success_count']/(self.state['success_count']+self.state['failure_count'])*100:.2f}%")
                    
        except KeyboardInterrupt:
            logger.warning("\n任务被中断!")
            logger.info(f"已保存进度，可使用 --resume 参数继续")
            self._save_state()
            sys.exit(0)
        except Exception as e:
            logger.error(f"任务出错: {str(e)}")
            self._save_state()
            raise
        
        # 任务完成
        logger.info("\n" + "="*60)
        logger.info("任务完成!")
        logger.info(f"  - 总处理药品: {self.state['processed_count']}")
        logger.info(f"  - 成功提取: {self.state['success_count']}")
        logger.info(f"  - 失败次数: {self.state['failure_count']}")
        logger.info(f"  - 总批次数: {current_batch}")
        logger.info(f"  - 输出目录: {self.output_dir}")
        logger.info("="*60)
    
    def merge_results(self, output_file: str = "tasks/output/all_diseases.json"):
        """合并所有批次结果
        
        Args:
            output_file: 输出文件路径
        """
        logger.info("开始合并批次结果...")
        
        all_extractions = []
        batch_files = sorted(self.output_dir.glob("batch_*.json"))
        
        for batch_file in tqdm(batch_files, desc="合并批次"):
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                all_extractions.extend(batch_data['extractions'])
        
        # 保存合并结果
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_extractions, f, ensure_ascii=False, indent=2)
        
        logger.info(f"合并完成!")
        logger.info(f"  - 总提取记录: {len(all_extractions)}")
        logger.info(f"  - 输出文件: {output_path}")
        
        # 统计独特疾病
        unique_diseases = set()
        for extraction in all_extractions:
            for disease in extraction.get('diseases', []):
                unique_diseases.add(disease['name'])
        
        logger.info(f"  - 独特疾病数: {len(unique_diseases)}")
        
        return all_extractions, unique_diseases
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_drugs': self.state['total_count'],
            'processed_drugs': self.state['processed_count'],
            'current_batch': self.state['current_batch'],
            'success_count': self.state['success_count'],
            'failure_count': self.state['failure_count'],
            'progress_percentage': (self.state['processed_count'] / self.state['total_count'] * 100) if self.state['total_count'] > 0 else 0,
            'last_updated': self.state['last_updated']
        }


def main():
    parser = argparse.ArgumentParser(
        description='疾病提取任务 - 支持分批处理和断点续传',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从头开始，每批处理100个
  python tasks/extract_diseases.py --batch-size 100
  
  # 从第10批开始
  python tasks/extract_diseases.py --start-from 10
  
  # 从上次中断处继续
  python tasks/extract_diseases.py --resume
  
  # 合并所有批次结果
  python tasks/extract_diseases.py --merge-only
  
  # 查看当前进度
  python tasks/extract_diseases.py --status
        """
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='每批处理的药品数量 (默认: 100)'
    )
    
    parser.add_argument(
        '--start-from',
        type=int,
        help='从指定批次开始 (0-based)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='从上次中断处继续'
    )
    
    parser.add_argument(
        '--merge-only',
        action='store_true',
        help='只合并已有的批次结果，不进行提取'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='显示当前任务状态'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='tasks/output/diseases',
        help='输出目录 (默认: tasks/output/diseases)'
    )
    
    args = parser.parse_args()
    
    # 初始化任务
    task = DiseaseExtractionTask(
        batch_size=args.batch_size,
        output_dir=args.output_dir
    )
    
    # 根据参数执行相应操作
    if args.status:
        # 显示状态
        stats = task.get_statistics()
        print("\n" + "="*60)
        print("任务状态")
        print("="*60)
        print(f"总药品数:     {stats['total_drugs']:,}")
        print(f"已处理:       {stats['processed_drugs']:,}")
        print(f"当前批次:     {stats['current_batch']}")
        print(f"成功提取:     {stats['success_count']:,}")
        print(f"失败次数:     {stats['failure_count']:,}")
        print(f"完成进度:     {stats['progress_percentage']:.2f}%")
        print(f"最后更新:     {stats['last_updated']}")
        print("="*60 + "\n")
        
    elif args.merge_only:
        # 只合并结果
        task.merge_results()
        
    else:
        # 运行提取任务
        if args.resume:
            logger.info("从上次中断处继续...")
            task.run()
        else:
            start_from = args.start_from if args.start_from is not None else 0
            task.run(start_from=start_from)
        
        # 完成后询问是否合并
        print("\n是否立即合并所有批次结果? [y/N]: ", end='')
        response = input().strip().lower()
        if response == 'y':
            task.merge_results()


if __name__ == '__main__':
    main()
