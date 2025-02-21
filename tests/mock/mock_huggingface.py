import json

class MockInferenceClient:
    def __init__(self, *args, **kwargs):
        pass

    def text_generation(self, prompt: str, *args, **kwargs):
        # Check the prompt content to determine which response to return
        if "急性链球菌性咽炎" in prompt:
            # Case 1
            mock_response = {
                "is_offlabel": False,
                "confidence": 0.95,
                "analysis": {
                    "indication_match": {
                        "score": 0.95,
                        "matching_indication": "急性链球菌性咽炎",
                        "reasoning": "阿莫西林是治疗急性链球菌性咽炎的标准用药之一，适应症完全匹配。"
                    },
                    "mechanism_similarity": {
                        "score": 1.0,
                        "reasoning": "阿莫西林作为β-内酰胺类抗生素，其作用机制与治疗链球菌性咽炎的需求完全吻合。"
                    },
                    "evidence_support": {
                        "level": "A",
                        "description": "多项随机对照试验和临床指南均支持使用阿莫西林治疗急性链球菌性咽炎。"
                    }
                },
                "recommendation": {
                    "decision": "建议使用",
                    "explanation": "阿莫西林是治疗急性链球菌性咽炎的一线用药，适应症完全匹配，有充分的循证医学证据支持。",
                    "risk_assessment": "常见不良反应包括胃肠道反应和皮疹，但总体风险较低。应注意是否有青霉素过敏史。"
                }
            }
        else:
            # Case 2 (default)
            mock_response = {
                "is_offlabel": True,
                "confidence": 0.85,
                "analysis": {
                    "indication_match": {
                        "score": 0.85,
                        "matching_indication": "肺动脉高压",
                        "reasoning": "西地那非用于治疗肺动脉高压有相关研究支持。"
                    },
                    "mechanism_similarity": {
                        "score": 0.9,
                        "reasoning": "西地那非通过抑制PDE5来改善肺动脉高压症状。"
                    },
                    "evidence_support": {
                        "level": "B",
                        "description": "多项临床研究支持西地那非用于治疗肺动脉高压。"
                    }
                },
                "recommendation": {
                    "decision": "谨慎使用",
                    "explanation": "虽然属于超适应症用药，但有研究证据支持其在肺动脉高压中的应用。",
                    "risk_assessment": "需要密切监测血压和心功能。"
                }
            }

        return json.dumps(mock_response)

def get_mock_inference_client():
    return MockInferenceClient()
