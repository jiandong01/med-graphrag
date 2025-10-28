"""
疾病提取任务 - 使用search_after API（ES最佳实践）
解决10000深度分页限制，保持高成功率

使用方法:
    python tasks/extract_diseases_search_after.py --concurrency 20 --batch-size 200
"""

import os
import sys
import json
import argparse
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from tqdm.asyncio import tqdm
import httpx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from app.src.utils import get_elastic_client, setup_logging, load_env

load_env()
logger = setup_logging("disease_extraction_search_after", log_dir="tasks/logs")


class AsyncDiseaseExtractionSearchAfter:
    """使用search_after API的异步疾病提取任务"""
    
    def __init__(
        self,
        batch_size: int = 200,
        concurrency: int = 20,
        output_dir: str = "tasks/output/diseases_search_after",
        state_file: str = "tasks/state/extraction_search_after_state.json"
    ):
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.output_dir = Path(output_dir)
        self.state_file = Path(state_file)
        self.model = "deepseek-chat"
        
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未配置 DEEPSEEK_API_KEY")
        
        self.api_base_url = "https://api.deepseek.com/v1/chat/completions"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.es = get_elastic_client()
        self.drugs_index = 'drugs'
        self.state = self._load_state()
        self.semaphore = asyncio.Semaphore(concurrency)
    
    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"加载状态: 已处理 {state['processed_count']} 个药品")
                return state
        else:
            return {
                'start_time': datetime.now().isoformat(),
                'processed_count': 0,
                'total_count': 0,
                'processed_drug_ids': set(),
                'current_batch': 0,
                'success_count': 0,
                'failure_count': 0,
                'last_sort_value': None,  # search_after关键参数
                'last_updated': datetime.now().isoformat()
            }
    
    def _save_state(self):
        state_to_save = self.state.copy()
        state_to_save['processed_drug_ids'] = list(self.state['processed_drug_ids'])
        state_to_save['last_updated'] = datetime.now().isoformat()
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, ensure_ascii=False, indent=2)
    
    def _generate_stable_id(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:32]
    
    def get_total_drugs_count(self) -> int:
        result = self.es.count(
            index=self.drugs_index,
            body={"query": {"exists": {"field": "indications"}}}
        )
        return result['count']
    
    def fetch_batch_with_search_after(self) -> Tuple[List[Dict[str, Any]], Optional[List]]:
        """使用search_after获取下一批（ES最佳实践，无10000限制）
        
        Returns:
            Tuple[List[Dict], Optional[List]]: (药品列表, 最后的sort值)
        """
        # 构建查询（使用create_time + id复合排序，确保唯一性）
        query = {
            "size": self.batch_size,
            "_source": ["id", "name", "indications"],
            "query": {
                "exists": {"field": "indications"}
            },
            "sort": [
                {"create_time": {"order": "asc", "unmapped_type": "date"}},
                {"id.keyword": {"order": "asc"}}  # 添加id作为第二排序，确保唯一性
            ]
        }
        
        # 如果有上次的排序值，使用search_after
        if self.state.get('last_sort_value'):
            query["search_after"] = self.state['last_sort_value']
        
        try:
            result = self.es.search(index=self.drugs_index, body=query)
            hits = result['hits']['hits']
            
            if not hits:
                return [], None
            
            # 过滤已处理的药品
            processed_ids_set = self.state['processed_drug_ids']
            filtered_drugs = [
                hit['_source'] 
                for hit in hits 
                if hit['_source']['id'] not in processed_ids_set
            ]
            
            # 保存最后的排序值
            last_sort = hits[-1]['sort'] if hits else None
            
            return filtered_drugs, last_sort
            
        except Exception as e:
            logger.error(f"ES查询失败: {str(e)}")
            raise
    
    async def extract_single_indication_async(
        self,
        client: httpx.AsyncClient,
        indication_text: str,
        drug_id: str,
        drug_name: str,
        retry_count: int = 3
    ) -> Optional[Dict[str, Any]]:
        async with self.semaphore:
            for attempt in range(retry_count):
                try:
                    prompt = f"""请从以下适应症文本中提取疾病信息。

适应症文本: {indication_text}

请严格按照以下JSON格式返回:
{{
  "diseases": [
    {{
      "name": "疾病名称",
      "type": "disease",
      "sub_diseases": [],
      "related_diseases": [],
      "confidence_score": 0.95
    }}
  ]
}}"""
                    
                    response = await client.post(
                        self.api_base_url,
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": "你是医学文本分析专家。只返回JSON，不要解释。"},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.3,
                            "max_tokens": 1500
                        }
                    )
                    
                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    
                    # 解析JSON
                    json_str = content
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        json_str = content[start:end].strip()
                    elif "```" in content:
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        json_str = content[start:end].strip()
                    
                    json_str = ''.join(c for c in json_str if c >= ' ' or c in ['\n', '\r', '\t'])
                    result = json.loads(json_str)
                    
                    return {
                        'id': self._generate_stable_id(indication_text),
                        'drug_id': drug_id,
                        'drug_name': drug_name,
                        'indication_text': indication_text,
                        'diseases': result.get('diseases', []),
                        'extraction_time': datetime.now().isoformat(),
                        'confidence': 0.95
                    }
                    
                except Exception as e:
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)
                        continue
                    return None
            
            return None
    
    async def process_batch_async(self, batch_drugs: List[Dict], batch_number: int) -> Dict[str, Any]:
        batch_results = {
            'batch_number': batch_number,
            'start_time': datetime.now().isoformat(),
            'drugs_count': len(batch_drugs),
            'extractions': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        tasks = []
        for drug in batch_drugs:
            indications = drug.get('indications', [])
            if isinstance(indications, str):
                indications = [indications]
            
            for indication in indications:
                if indication and indication.strip():
                    tasks.append((indication, drug['id'], drug['name']))
        
        timeout = httpx.Timeout(60.0, connect=15.0, read=60.0, write=10.0)
        limits = httpx.Limits(
            max_keepalive_connections=self.concurrency,
            max_connections=self.concurrency * 2
        )
        
        async with httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout,
            limits=limits
        ) as client:
            extraction_tasks = [
                self.extract_single_indication_async(client, ind, did, dname)
                for ind, did, dname in tasks
            ]
            
            for coro in tqdm.as_completed(
                extraction_tasks,
                desc=f"批次 {batch_number}",
                total=len(extraction_tasks),
                leave=False
            ):
                result = await coro
                
                if result:
                    batch_results['extractions'].append(result)
                    batch_results['success_count'] += 1
                else:
                    batch_results['failure_count'] += 1
        
        for drug in batch_drugs:
            self.state['processed_drug_ids'].add(drug['id'])
            self.state['processed_count'] += 1
        
        batch_results['end_time'] = datetime.now().isoformat()
        return batch_results
    
    def save_batch_results(self, batch_results: Dict[str, Any]):
        batch_file = self.output_dir / f"batch_{batch_results['batch_number']:05d}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
        
        elapsed = (
            datetime.fromisoformat(batch_results['end_time']) - 
            datetime.fromisoformat(batch_results['start_time'])
        ).total_seconds()
        
        success_rate = (batch_results['success_count'] / 
                       (batch_results['success_count'] + batch_results['failure_count']) * 100
                       if (batch_results['success_count'] + batch_results['failure_count']) > 0 else 0)
        
        logger.info(f"批次 {batch_results['batch_number']} | 耗时{elapsed:.0f}s | 成功{batch_results['success_count']} | 失败{batch_results['failure_count']} | 成功率{success_rate:.1f}%")
    
    async def run_async(self):
        if isinstance(self.state['processed_drug_ids'], list):
            self.state['processed_drug_ids'] = set(self.state['processed_drug_ids'])
        
        if self.state['total_count'] == 0:
            self.state['total_count'] = self.get_total_drugs_count()
            logger.info(f"总药品数: {self.state['total_count']}")
        
        logger.info(f"开始处理 (并发度={self.concurrency}, 批次={self.batch_size})")
        logger.info(f"  已处理: {self.state['processed_count']}")
        logger.info(f"  当前批次: {self.state['current_batch']}")
        
        overall_start = datetime.now()
        current_batch = self.state['current_batch']
        
        try:
            while self.state['processed_count'] < self.state['total_count']:
                # 使用search_after获取下一批
                batch_drugs, last_sort = self.fetch_batch_with_search_after()
                
                if not batch_drugs:
                    logger.info("无更多数据")
                    break
                
                logger.info(f"\n批次 {current_batch} | 获取{len(batch_drugs)}个药品")
                
                batch_results = await self.process_batch_async(batch_drugs, current_batch)
                self.save_batch_results(batch_results)
                
                # 检查批次成功率
                batch_total = batch_results['success_count'] + batch_results['failure_count']
                if batch_total > 0:
                    batch_success_rate = (batch_results['success_count'] / batch_total) * 100
                    if batch_success_rate < 99.0:
                        logger.error(f"⚠️  批次成功率过低 ({batch_success_rate:.1f}%)，自动停止!")
                        logger.error(f"可能原因: API余额不足或网络问题")
                        logger.error(f"请检查API状态后重新运行: --resume")
                        self._save_state()
                        sys.exit(1)
                
                # 更新状态
                self.state['current_batch'] = current_batch + 1
                self.state['success_count'] += batch_results['success_count']
                self.state['failure_count'] += batch_results['failure_count']
                self.state['last_sort_value'] = last_sort  # 保存sort值
                self._save_state()
                
                current_batch += 1
                
                # 统计
                elapsed = (datetime.now() - overall_start).total_seconds()
                speed = self.state['processed_count'] / (elapsed / 3600) if elapsed > 0 else 0
                remaining = self.state['total_count'] - self.state['processed_count']
                eta_hours = remaining / speed if speed > 0 else 0
                
                success_rate = (
                    self.state['success_count'] / 
                    (self.state['success_count'] + self.state['failure_count']) * 100
                    if (self.state['success_count'] + self.state['failure_count']) > 0 
                    else 0
                )
                
                logger.info(f"📊 进度{self.state['processed_count']}/{self.state['total_count']} ({self.state['processed_count']/self.state['total_count']*100:.1f}%) | 成功率{success_rate:.2f}% | 速度{speed:.0f}/h | ETA{eta_hours:.1f}h")
                
        except KeyboardInterrupt:
            logger.warning("中断! 进度已保存")
            self._save_state()
            sys.exit(0)
        except Exception as e:
            logger.error(f"错误: {str(e)}")
            self._save_state()
            raise
        
        logger.info("任务完成!")
    
    def run(self):
        asyncio.run(self.run_async())
    
    def get_statistics(self) -> Dict[str, Any]:
        total = self.state['success_count'] + self.state['failure_count']
        success_rate = (self.state['success_count'] / total * 100) if total > 0 else 0
        
        return {
            'total_drugs': self.state['total_count'],
            'processed_drugs': self.state['processed_count'],
            'current_batch': self.state['current_batch'],
            'success_count': self.state['success_count'],
            'failure_count': self.state['failure_count'],
            'success_rate': success_rate,
            'progress': self.state['processed_count'] / self.state['total_count'] * 100 if self.state['total_count'] > 0 else 0,
            'concurrency': self.concurrency,
            'batch_size': self.batch_size
        }


def main():
    parser = argparse.ArgumentParser(description='疾病提取 - search_after版')
    parser.add_argument('--concurrency', type=int, default=20, help='并发数 (推荐: 20)')
    parser.add_argument('--batch-size', type=int, default=200, help='批次大小')
    parser.add_argument('--resume', action='store_true', help='继续')
    parser.add_argument('--status', action='store_true', help='状态')
    
    args = parser.parse_args()
    
    task = AsyncDiseaseExtractionSearchAfter(
        batch_size=args.batch_size,
        concurrency=args.concurrency
    )
    
    if args.status:
        stats = task.get_statistics()
        print(f"\n异步版 (search_after, 并发={stats['concurrency']})")
        print(f"已处理: {stats['processed_drugs']:,}/{stats['total_drugs']:,} ({stats['progress']:.1f}%)")
        print(f"成功: {stats['success_count']:,} | 失败: {stats['failure_count']:,} | 成功率: {stats['success_rate']:.2f}%\n")
    else:
        task.run()


if __name__ == '__main__':
    try:
        import httpx
    except ImportError:
        print("需要: pip install httpx")
        sys.exit(1)
    
    main()
