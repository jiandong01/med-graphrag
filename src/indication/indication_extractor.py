import os
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm
from huggingface_hub import InferenceClient

# 导入utils中的load_env函数
from src.utils import load_env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndicationExtractor:
    def __init__(self, api_key: str = None):
        """初始化提取器
        
        Args:
            api_key: HuggingFace API key
        """
        # 加载环境变量
        load_env()
        
        self.api_key = api_key or os.getenv('HF_API_KEY')
        if not self.api_key:
            raise ValueError("HF_API_KEY not found")
        
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key
        )
        
        self.base_dir = None     # 基础输出目录
        self.output_dir = None   # 提取结果输出目录
        self.log_dir = None      # 日志输出目录
        self.processed_count = 0  # 处理计数
        self.save_interval = 10   # 每处理10个保存一次
        
        # 初始化日志文件
        self.success_log = None
        self.failure_log = None
        
    def init_output_dirs(self, base_dir: str):
        """初始化输出目录结构
        
        Args:
            base_dir: 基础输出目录
        """
        self.base_dir = Path(base_dir)
        
        # 创建时间戳子目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 创建提取结果目录
        self.output_dir = self.base_dir / f"extracted_indications_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志目录
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志文件
        self.success_log = open(self.log_dir / f'success_{timestamp}.log', 'w', encoding='utf-8')
        self.failure_log = open(self.log_dir / f'failure_{timestamp}.log', 'w', encoding='utf-8')
        
    def close_logs(self):
        """关闭日志文件"""
        if self.success_log:
            self.success_log.close()
        if self.failure_log:
            self.failure_log.close()

    def process_indications(self, input_file: str, output_dir: str) -> None:
        """处理所有适应症
        
        Args:
            input_file: 输入文件路径
            output_dir: 输出目录路径
        """
        # 初始化输出目录结构
        self.init_output_dirs(output_dir)
        
        try:
            # 读取输入文件
            with open(input_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                data = raw_data.get('data', [])  # 从'data'字段获取数据
                
            logger.info(f"Loaded {len(data)} indications from {input_file}")
            
            # 处理每个适应症
            results = []
            for indication in tqdm(data, desc="Processing indications"):
                result = self.process_indication(indication)
                if result:
                    results.append(result)
                    self.save_result(result)  # 保存单个结果
                    self.log_success(result['drug_ids'])  # 记录成功
                    
                    # 定期保存所有结果
                    self.processed_count += 1
                    if self.processed_count % self.save_interval == 0:
                        logger.info(f"Processed {self.processed_count} indications")
            
            logger.info(f"Finished processing {len(results)} indications")
            
        finally:
            # 确保关闭日志文件
            self.close_logs()
            
    def save_result(self, result: Dict) -> None:
        """保存单个处理结果
        
        Args:
            result: 处理结果
        """
        try:
            # 为每个drug_id保存一个文件
            for drug_id in result['drug_ids']:
                filename = f"{drug_id}.json"
                filepath = self.output_dir / filename
                
                # 如果文件已存在，读取并更新
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, list):
                            existing_data.append(result)
                        else:
                            existing_data = [existing_data, result]
                else:
                    existing_data = [result]
                
                # 保存更新后的数据
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, ensure_ascii=False, indent=2, fp=f)
                
        except Exception as e:
            logger.error(f"Error saving result: {e}")

    def create_extraction_prompt(self, text: str) -> list:
        """创建实体抽取的prompt
        
        Args:
            text: 适应症文本
            
        Returns:
            list: prompt消息列表
        """
        system_message = {
            "role": "system",
            "content": """你是一个医学文本分析专家。请从医药说明书的适应症文本中抽取疾病相关信息，直接输出JSON格式，不要包含任何其他内容。

输出格式要求：
{
  "diseases": [
    {
      "name": "主要疾病名称",      // 主要疾病
      "type": "disease",         // 固定为"disease"
      "sub_diseases": [          // 子疾病/具体表现，可选
        {
          "name": "子疾病名称",
          "attributes": {        // 属性信息，可选
            "severity": "严重程度",  // 如：轻度、中度、重度、轻中度等
            "stage": "疾病阶段",    // 如：早期、晚期等
            "type": "疾病类型"      // 疾病的具体类型
          }
        }
      ],
      "related_diseases": [      // 相关疾病，可选
        {
          "name": "相关疾病名称",
          "attributes": {        // 属性信息，可选
            "severity": "严重程度",
            "stage": "疾病阶段",
            "type": "疾病类型"
          },
          "relationship": "complication"  // 关系类型，如：并发症、后遗症、症状、病因等
        }
      ],
      "confidence_score": 0.95   // 对本疾病及其关联信息的提取置信度，0-1之间
    }
  ]
}

注意事项：
1. 每个疾病必须包含name、type和confidence_score字段
2. confidence_score表示对该疾病信息提取的置信度：
   - 0.9-1.0: 非常确信，文本明确指出了疾病及其属性
   - 0.7-0.9: 比较确信，大部分信息明确，可能有少许推断
   - 0.5-0.7: 中等确信，部分信息需要推断
   - <0.5: 低确信，信息模糊或需要大量推断
3. attributes对象是可选的，但如果存在，应该包含具体的属性信息
4. relationship应该准确描述疾病之间的关系，常见值包括：
   - complication: 并发症
   - symptom: 症状
   - cause: 病因
   - sequela: 后遗症
5. 如果文本中包含多个独立的疾病，应该分别列出
6. 严重程度应标准化为：轻度、中度、重度、轻中度、中重度
7. 疾病阶段应标准化为：早期、中期、晚期、急性期、慢性期等"""
        }
        
        user_message = {
            "role": "user",
            "content": f"请从以下适应症文本中抽取疾病相关信息：\n\n{text}"
        }
        
        return [system_message, user_message]

    def extract_diseases(self, text: str) -> Optional[Dict]:
        """从适应症文本中抽取疾病信息
        
        Args:
            text: 适应症文本
            
        Returns:
            Optional[Dict]: 提取的疾病信息，如果提取失败则返回None
        """
        try:
            messages = self.create_extraction_prompt(text)
            logger.debug(f"Sending request to API with text: {text}")
            
            raw_response = self.client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                messages=messages,
                max_tokens=4000,
                temperature=0.1
            )
            
            completion = raw_response.choices[0].message.content
            logger.debug(f"Raw API response: {raw_response}")
            
            # 解析响应，保留think标签
            try:
                # # 提取think标签内容（如果有）
                # think_content = None
                # think_match = re.search(r'<think>(.*?)</think>', response_content, re.DOTALL)
                # if think_match:
                #     think_content = think_match.group(1).strip()
                
                # 尝试提取JSON部分
                json_content = None
                # 首先尝试直接解析整个响应
                try:
                    result = json.loads(completion)
                    json_content = completion
                except json.JSONDecodeError:
                    # 如果失败，尝试在响应中查找JSON部分
                    json_start = completion.find('{')
                    json_end = completion.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_content = completion[json_start:json_end]
                        result = json.loads(json_content)
                    else:
                        raise ValueError("No valid JSON found in completion")
                
                # 验证结果格式
                if not isinstance(result, dict) or 'diseases' not in result:
                    raise ValueError("Invalid result format: missing required fields")
                
                # 添加原始响应信息到结果中
                result['_raw_response'] = raw_response
                
                return result
                
            except Exception as je:
                # 记录解析失败
                self.log_failure([], text, messages, raw_response, str(je))
                logger.error(f"Failed to parse API response: {str(je)}")
                return None
            
        except Exception as e:
            # 记录API调用失败
            self.log_failure([], text, messages, None, str(e))
            logger.error(f"Error calling API: {str(e)}")
            return None
    
    def process_indication(self, indication: Dict) -> Dict:
        """处理单个适应症
        
        Args:
            indication: 原始适应症数据
            
        Returns:
            Dict: 处理后的适应症数据
        """
        try:
            # 提取疾病信息
            extraction_result = self.extract_diseases(indication['text'])
            if not extraction_result:
                # 记录处理失败
                self.log_failure(
                    [drug['id'] for drug in indication['drugs']], 
                    indication['text'],
                    {'text': indication['text']},
                    None,
                    "Failed to extract diseases"
                )
                logger.warning(f"Failed to extract diseases from text: {indication['text']}")
                return None
            
            # DEBUG: 输出原始响应
            raw_response = extraction_result.get('_raw_response', {})
            logger.info("\n" + "="*80)
            logger.info(f"Processing text: {indication['text']}")
            
            # 输出完整的响应内容
            logger.info("\nRaw API Response Usage:")
            logger.info(raw_response.get('usage', 'No usage available'))
            
            # 输出解析后的结果
            logger.info("\nExtracted result:")
            logger.info(json.dumps(extraction_result['diseases'], ensure_ascii=False, indent=2))
            logger.info("="*80)
            
            # 获取原始响应信息
            raw_response = extraction_result.pop('_raw_response', None)
            
            # 计算整体置信度（所有疾病的平均置信度）
            confidence_scores = [
                disease.get('confidence_score', 0.5) 
                for disease in extraction_result['diseases']
            ]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            # 构建结果
            result = {
                'id': indication['id'],  # 使用原始ID
                'diseases': extraction_result['diseases'],
                'source_text': indication['text'],
                'drug_ids': [drug['id'] for drug in indication['drugs']],
                'metadata': {
                    'extraction_time': datetime.now().isoformat(),
                    'confidence': avg_confidence,  # 使用计算的平均置信度
                    'raw_response': raw_response  # 添加原始响应信息
                }
            }
            
            # 标准化疾病信息
            for disease in result['diseases']:
                # 确保必要字段存在
                disease['type'] = disease.get('type', 'disease')
                if 'confidence_score' not in disease:
                    disease['confidence_score'] = 0.5  # 默认置信度
                
                # 标准化子疾病
                if 'sub_diseases' in disease:
                    for sub in disease['sub_diseases']:
                        if 'attributes' not in sub:
                            sub['attributes'] = {}
                
                # 标准化相关疾病
                if 'related_diseases' in disease:
                    for rel in disease['related_diseases']:
                        if 'attributes' not in rel:
                            rel['attributes'] = {}
                        # 标准化relationship
                        if rel.get('relationship') == '原因':
                            rel['relationship'] = 'cause'
                        elif rel.get('relationship') == '症状':
                            rel['relationship'] = 'symptom'
                        elif rel.get('relationship') == '并发症':
                            rel['relationship'] = 'complication'
                        elif rel.get('relationship') == '后遗症':
                            rel['relationship'] = 'sequela'
                
                # 标准化属性值
                if 'attributes' in disease:
                    attrs = disease['attributes']
                    if 'severity' in attrs:
                        # 标准化严重程度
                        severity_map = {
                            '轻': '轻度',
                            '中': '中度',
                            '重': '重度',
                            '轻中': '轻中度',
                            '中重': '中重度'
                        }
                        for old, new in severity_map.items():
                            if attrs['severity'].startswith(old):
                                attrs['severity'] = new
                                break
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing indication: {str(e)}")
            return None
    
    def log_success(self, drug_ids: List[str]):
        """记录成功的请求
        
        Args:
            drug_ids: 药品ID列表
        """
        if self.success_log:
            for drug_id in drug_ids:
                self.success_log.write(f"{datetime.now().isoformat()} - {drug_id}\n")
            self.success_log.flush()
            
    def log_failure(self, drug_ids: List[str], text: str, request: Dict, response: Any, error: str = None):
        """记录失败的请求
        
        Args:
            drug_ids: 药品ID列表
            text: 原始文本
            request: 请求内容
            response: API响应
            error: 错误信息
        """
        if self.failure_log:
            self.failure_log.write(f"\n{'='*80}\n")
            self.failure_log.write(f"Time: {datetime.now().isoformat()}\n")
            self.failure_log.write(f"Drug IDs: {', '.join(drug_ids)}\n")
            self.failure_log.write(f"Original Text: {text}\n")
            self.failure_log.write(f"Request: {json.dumps(request, ensure_ascii=False, indent=2)}\n")
            self.failure_log.write(f"Response: {json.dumps(response, ensure_ascii=False, indent=2) if response else 'No response'}\n")
            if error:
                self.failure_log.write(f"Error: {error}\n")
            self.failure_log.write(f"{'='*80}\n")
            self.failure_log.flush()

def main():
    parser = argparse.ArgumentParser(description='Extract structured disease information from indications')
    parser.add_argument('--input', type=str, required=True,
                      help='Input JSON file containing raw indications')
    parser.add_argument('--output', type=str, required=True,
                      help='Output directory for storing results and logs')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return
    
    # 创建抽取器并处理文件
    api_key = os.getenv('HF_API_KEY')
    extractor = IndicationExtractor(api_key)
    extractor.process_indications(args.input, args.output)

if __name__ == '__main__':
    main()
