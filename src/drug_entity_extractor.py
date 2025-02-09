from huggingface_hub import InferenceClient
import json
import logging
from typing import Dict, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DrugEntityGenerator:
    def __init__(self, api_key: str):
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=api_key
        )
        
    def create_extraction_prompt(self, text: str) -> list:
        """创建实体抽取的prompt"""
        system_message = {
            "role": "system",
            "content": """你是一个医学文本分析专家，专门负责从医药说明书中抽取适应症相关实体。
请按照以下JSON格式输出结果：
{
    "entities": [
        {
            "id": "e1",
            "text": "疾病名称",
            "type": "disease",
            "medical_system": "western或tcm",
            "standard_name": "标准化名称",
            "attributes": {
                "pathogen": "病原体（如果有）",
                "body_part": "相关部位（如果有）"
            }
        }
    ],
    "relations": [
        {
            "head": "源疾病",
            "tail": "目标疾病",
            "type": "关系类型",
            "evidence_level": "A/B/C",
            "source": "说明书"
        }
    ],
    "metadata": {
        "original_text": "原始文本",
        "processing_notes": "处理说明",
        "confidence_score": 0.95
    }
}"""
        }
        
        user_message = {
            "role": "user",
            "content": f"请从以下医药说明书文本中抽取适应症相关实体和关系：\n\n{text}"
        }
        
        return [system_message, user_message]

    def extract_entities(self, text: str) -> Optional[Dict]:
        """调用API进行实体抽取"""
        try:
            messages = self.create_extraction_prompt(text)
            completion = self.client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                messages=messages,
                max_tokens=2000,
                temperature=0.1
            )
            
            result = json.loads(completion.choices[0].message.content)
            result['metadata']['extraction_time'] = datetime.now().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return None

    def process_batch(self, texts: list, output_dir: str = "outputs"):
        """批量处理文本并保存结果"""
        Path(output_dir).mkdir(exist_ok=True)
        
        results = []
        for i, text in enumerate(texts):
            logger.info(f"Processing text {i+1}/{len(texts)}")
            result = self.extract_entities(text)
            if result:
                results.append(result)
                
                # 保存单条结果
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"{output_dir}/extraction_{timestamp}_{i}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
        
        return results

def main():
    # 加载配置
    utils.load_env()
    config = utils.load_config()
    logger = utils.setup_logging('generate_drug_entity', config)
    utils.ensure_directories(config)
    
    # 初始化生成器
    generator = DrugEntityGenerator(os.getenv('HF_API_KEY'))
    
    # 获取数据库配置
    db_configs = utils.get_db_configs()
    
    # 读取需要处理的文本
    engine = create_engine(
        f"postgresql://{db_configs['postgresql']['user']}:{db_configs['postgresql']['password']}"
        f"@{db_configs['postgresql']['host']}:{db_configs['postgresql']['port']}"
        f"/{db_configs['postgresql']['dbname']}"
    )
    
    query = "SELECT id, content FROM indication_table WHERE processed = FALSE LIMIT 10"
    df = pd.read_sql(query, engine)
    
    # 批量处理
    results = generator.process_batch(df['content'].tolist(), config['paths']['output_dir'])
    
    # 将结果保存到临时文件
    output_file = Path(config['paths']['output_dir']) / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Processing completed. Results saved to {output_file}")