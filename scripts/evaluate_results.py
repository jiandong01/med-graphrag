"""评估系统判断结果：计算precision、recall、F1、AUC、ROC等"""

import json
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

# 绘图库（可选）
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("提示: 安装matplotlib可以绘制ROC曲线图")
    print("  pip install matplotlib")

def load_results(jsonl_file: str) -> List[Dict]:
    """加载分析结果"""
    results = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results

def calculate_auc_roc(y_true: List[bool], y_scores: List[float]) -> Tuple[float, List[Dict]]:
    """计算AUC和ROC曲线数据
    
    Args:
        y_true: 真实标签
        y_scores: 预测分数（越高越可能是正例）
        
    Returns:
        (auc, roc_points): AUC值和ROC曲线点列表
    """
    # 转换为numpy数组
    y_true = np.array([1 if t else 0 for t in y_true])
    y_scores = np.array(y_scores)
    
    # 获取唯一的阈值
    thresholds = np.unique(y_scores)
    thresholds = np.sort(thresholds)[::-1]  # 降序
    
    # 计算每个阈值下的TPR和FPR
    roc_points = []
    
    for threshold in thresholds:
        y_pred_at_threshold = (y_scores >= threshold).astype(int)
        
        TP = np.sum((y_true == 1) & (y_pred_at_threshold == 1))
        FP = np.sum((y_true == 0) & (y_pred_at_threshold == 1))
        TN = np.sum((y_true == 0) & (y_pred_at_threshold == 0))
        FN = np.sum((y_true == 1) & (y_pred_at_threshold == 0))
        
        TPR = TP / (TP + FN) if (TP + FN) > 0 else 0  # 真正例率 (召回率)
        FPR = FP / (FP + TN) if (FP + TN) > 0 else 0  # 假正例率
        
        roc_points.append({
            'threshold': float(threshold),
            'tpr': float(TPR),
            'fpr': float(FPR)
        })
    
    # 添加(0,0)和(1,1)点
    roc_points.insert(0, {'threshold': float('inf'), 'tpr': 0.0, 'fpr': 0.0})
    roc_points.append({'threshold': float('-inf'), 'tpr': 1.0, 'fpr': 1.0})
    
    # 使用梯形法则计算AUC
    fpr_values = [p['fpr'] for p in roc_points]
    tpr_values = [p['tpr'] for p in roc_points]
    auc = np.trapz(tpr_values, fpr_values)
    
    return abs(auc), roc_points

def plot_roc_curve(roc_points: List[Dict], auc: float, output_file: str = "data/raw/clinical_cases/roc_curve.png"):
    """绘制ROC曲线
    
    Args:
        roc_points: ROC曲线点列表
        auc: AUC值
        output_file: 输出图片文件路径
    """
    if not MATPLOTLIB_AVAILABLE:
        print("\n⚠️  无法绘制ROC曲线：matplotlib未安装")
        print("   安装方法: pip install matplotlib")
        return
    
    # 提取FPR和TPR
    fpr = [p['fpr'] for p in roc_points]
    tpr = [p['tpr'] for p in roc_points]
    
    # 创建图形
    plt.figure(figsize=(8, 6))
    
    # 绘制ROC曲线
    plt.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC Curve (AUC={auc:.3f})')
    
    # 绘制对角线（随机猜测）
    plt.plot([0, 1], [0, 1], 'r--', linewidth=1, label='Random Guess')
    
    # 设置图形
    plt.xlabel('False Positive Rate (FPR)', fontsize=12)
    plt.ylabel('True Positive Rate (TPR)', fontsize=12)
    plt.title('ROC Curve - Off-label Use', fontsize=14, fontweight='bold')
    plt.legend(loc='lower right', fontsize=10)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.0])
    
    # 添加文本注释
    plt.text(0.6, 0.2, f'AUC = {auc:.3f}', 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            fontsize=12)
    
    # 保存图片
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ ROC曲线图已保存: {output_file}")
    plt.close()

def enrich_drug_info(drug_info: Dict) -> Dict:
    """从ES补充药品详细信息
    
    Args:
        drug_info: 基本药品信息
        
    Returns:
        Dict: 补充了详细信息的药品信息
    """
    from app.shared import get_es_client
    
    drug_id = drug_info.get('id')
    if not drug_id:
        return drug_info
    
    try:
        es = get_es_client()
        result = es.get(index='drugs', id=drug_id)
        source = result['_source']
        
        # 补充详细信息
        drug_info['indications_list'] = source.get('indications_list', [])
        drug_info['indications'] = source.get('indications', [])
        drug_info['contraindications'] = source.get('contraindications', [])
        
        return drug_info
    except Exception as e:
        print(f"⚠️  无法从ES获取药品详细信息: {str(e)}")
        return drug_info

def evaluate_results(results: List[Dict], plot_roc: bool = True):
    """评估结果"""
    
    print("="*80)
    print("评估结果分析")
    print("="*80)
    
    # 过滤有效数据（排除错误、药品信息缺失和无效判断）
    valid_results = []
    skipped_no_drug = 0
    skipped_error = 0
    skipped_invalid_judgment = 0
    
    for r in results:
        # 跳过有错误的记录
        if 'error' in r['system_analysis'].get('analysis_details', {}):
            skipped_error += 1
            continue
        
        # 跳过药品信息缺失的记录（is_offlabel 为 null）
        if r['system_analysis'].get('is_offlabel') is None:
            skipped_no_drug += 1
            continue
        
        # 跳过无效的人工判断
        if r['manual_judgment'] not in ['是', '否']:
            skipped_invalid_judgment += 1
            continue
        
        valid_results.append(r)
    
    print(f"\n数据过滤:")
    print(f"  总计: {len(results)} 条")
    print(f"  跳过（药品信息缺失）: {skipped_no_drug} 条")
    print(f"  跳过（分析错误）: {skipped_error} 条")
    print(f"  跳过（人工判断无效）: {skipped_invalid_judgment} 条")
    print(f"  有效数据: {len(valid_results)} 条")
    
    if not valid_results:
        print("没有有效数据可评估")
        return
    
    # 转换为二分类
    # 人工标注: "是" -> True (超适应症), "否" -> False (非超适应症)
    # 系统判断: is_offlabel: True/False
    
    y_true = []  # 人工标注
    y_pred = []  # 系统判断
    y_scores = []  # 预测分数（用于AUC-ROC）
    
    for r in valid_results:
        manual = r['manual_judgment'] == '是'  # True=超适应症
        system = r['system_analysis'].get('is_offlabel', True)
        
        # 获取预测分数：使用rule_confidence的反值
        # rule_confidence=1.0表示精确匹配（非超适应症），分数应该低
        # rule_confidence=0.0表示无匹配（超适应症），分数应该高
        metadata = r['system_analysis'].get('metadata', {})
        rule_conf = metadata.get('rule_confidence', 0.0)
        
        # 计算超适应症倾向分数：1.0 - rule_confidence
        # score=1.0 表示高度倾向超适应症
        # score=0.0 表示低度倾向超适应症（即标准用药）
        score = 1.0 - rule_conf
        
        y_true.append(manual)
        y_pred.append(system)
        y_scores.append(score)
    
    # 计算混淆矩阵
    TP = sum(1 for t, p in zip(y_true, y_pred) if t == True and p == True)   # 真正例：正确识别为超适应症
    TN = sum(1 for t, p in zip(y_true, y_pred) if t == False and p == False) # 真负例：正确识别为非超适应症
    FP = sum(1 for t, p in zip(y_true, y_pred) if t == False and p == True)  # 假正例：误判为超适应症
    FN = sum(1 for t, p in zip(y_true, y_pred) if t == True and p == False)  # 假负例：漏判超适应症
    
    print(f"\n混淆矩阵:")
    print(f"                 预测")
    print(f"           超适应症  非超适应症")
    print(f"实际 超适应症  {TP:4d}     {FN:4d}")
    print(f"     非超适应症  {FP:4d}     {TN:4d}")
    
    # 计算指标
    accuracy = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # 计算AUC-ROC
    try:
        auc, roc_points = calculate_auc_roc(y_true, y_scores)
        print(f"\n评估指标:")
        print(f"  Accuracy:  {accuracy:.3f} ({accuracy*100:.1f}%)")
        print(f"  Precision: {precision:.3f} ({precision*100:.1f}%)")  # 判定为超适应症的准确率
        print(f"  Recall:    {recall:.3f} ({recall*100:.1f}%)")      # 超适应症的召回率
        print(f"  F1-Score:  {f1:.3f}")
        print(f"  AUC:       {auc:.3f}")  # ROC曲线下面积
        
        # 显示部分ROC点
        print(f"\nROC曲线关键点:")
        print(f"  {'阈值':<10} {'FPR':<10} {'TPR':<10}")
        for point in roc_points[::max(1, len(roc_points)//10)][:10]:  # 显示10个代表性点
            threshold = point['threshold']
            if threshold == float('inf'):
                threshold_str = "∞"
            elif threshold == float('-inf'):
                threshold_str = "-∞"
            else:
                threshold_str = f"{threshold:.3f}"
            print(f"  {threshold_str:<10} {point['fpr']:.3f}      {point['tpr']:.3f}")
    except Exception as e:
        print(f"\n计算AUC-ROC时出错: {str(e)}")
        auc = None
        roc_points = []
        
        print(f"\n评估指标:")
        print(f"  Accuracy:  {accuracy:.3f} ({accuracy*100:.1f}%)")
        print(f"  Precision: {precision:.3f} ({precision*100:.1f}%)")
        print(f"  Recall:    {recall:.3f} ({recall*100:.1f}%)")
        print(f"  F1-Score:  {f1:.3f}")
    
    # 详细分析
    print(f"\n详细分析:")
    print(f"  总样本数: {len(valid_results)}")
    print(f"  人工判断为超适应症: {sum(y_true)}")
    print(f"  人工判断为非超适应症: {len(y_true) - sum(y_true)}")
    print(f"  系统判断为超适应症: {sum(y_pred)}")
    print(f"  系统判断为非超适应症: {len(y_pred) - sum(y_pred)}")
    
    # 错误案例详细分析和导出
    print("\n正在从ES补充药品详细信息...")
    fp_detailed_cases = []
    fn_detailed_cases = []
    
    for r, t, p in zip(valid_results, y_true, y_pred):
        if t == False and p == True:
            # 假正例：误判为超适应症
            drug_info = r['system_analysis'].get('drug_info', {})
            # 从ES补充药品详细信息
            drug_info_enriched = enrich_drug_info(drug_info.copy())
            
            fp_detailed_cases.append({
                'row_number': r['row_number'],
                'drug_name': r['drug_name'],
                'disease_name': r['disease_name'],
                'manual_judgment': r['manual_judgment'],
                'system_judgment': '是',
                'drug_info': drug_info_enriched,
                'disease_info': r['system_analysis'].get('disease_info', {}),
                'analysis_details': r['system_analysis'].get('analysis_details', {}),
                'metadata': r['system_analysis'].get('metadata', {})
            })
        elif t == True and p == False:
            # 假负例：漏判超适应症
            drug_info = r['system_analysis'].get('drug_info', {})
            # 从ES补充药品详细信息
            drug_info_enriched = enrich_drug_info(drug_info.copy())
            
            fn_detailed_cases.append({
                'row_number': r['row_number'],
                'drug_name': r['drug_name'],
                'disease_name': r['disease_name'],
                'manual_judgment': r['manual_judgment'],
                'system_judgment': '否',
                'drug_info': drug_info_enriched,
                'disease_info': r['system_analysis'].get('disease_info', {}),
                'analysis_details': r['system_analysis'].get('analysis_details', {}),
                'metadata': r['system_analysis'].get('metadata', {})
            })
    
    # 显示错误案例摘要
    if FP > 0:
        print(f"\n假正例（误判为超适应症）: {FP} 个")
        print(f"前5个案例:")
        for i, case in enumerate(fp_detailed_cases[:5], 1):
            print(f"  {i}. {case['drug_name']} + {case['disease_name']}")
            print(f"     药品: {case['drug_info'].get('standard_name', 'N/A')}")
            print(f"     适应症匹配: {case['analysis_details'].get('indication_match', {}).get('reasoning', 'N/A')[:80]}...")
    
    if FN > 0:
        print(f"\n假负例（漏判超适应症）: {FN} 个")
        print(f"前5个案例:")
        for i, case in enumerate(fn_detailed_cases[:5], 1):
            print(f"  {i}. {case['drug_name']} + {case['disease_name']}")
            print(f"     药品: {case['drug_info'].get('standard_name', 'N/A')}")
    
    # 导出详细错误案例
    if fp_detailed_cases or fn_detailed_cases:
        error_cases_file = "data/raw/clinical_cases/error_cases_detailed.json"
        error_cases_data = {
            'false_positives': fp_detailed_cases,
            'false_negatives': fn_detailed_cases,
            'summary': {
                'fp_count': len(fp_detailed_cases),
                'fn_count': len(fn_detailed_cases),
                'total_errors': len(fp_detailed_cases) + len(fn_detailed_cases)
            }
        }
        
        with open(error_cases_file, 'w', encoding='utf-8') as f:
            json.dump(error_cases_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细错误案例已导出到: {error_cases_file}")
        print(f"  假正例: {len(fp_detailed_cases)} 个")
        print(f"  假负例: {len(fn_detailed_cases)} 个")
    
    # 保存评估报告
    report = {
        'total_samples': len(valid_results),
        'confusion_matrix': {
            'TP': TP,
            'TN': TN,
            'FP': FP,
            'FN': FN
        },
        'metrics': {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'auc': auc if auc is not None else None
        },
        'distribution': {
            'manual_yes': sum(y_true),
            'manual_no': len(y_true) - sum(y_true),
            'system_yes': sum(y_pred),
            'system_no': len(y_pred) - sum(y_pred)
        },
        'roc_curve': roc_points if roc_points else []
    }
    
    report_file = "data/raw/clinical_cases/evaluation_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n评估报告已保存到: {report_file}")
    
    # 绘制ROC曲线
    if plot_roc and auc is not None and roc_points:
        plot_roc_curve(roc_points, auc)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='评估系统判断结果')
    parser.add_argument('--input', default='data/raw/clinical_cases/超说明书用药判断结果-系统分析.jsonl',
                       help='JSONL结果文件')
    parser.add_argument('--no-plot', action='store_true',
                       help='不绘制ROC曲线图')
    
    args = parser.parse_args()
    
    # 加载结果
    results = load_results(args.input)
    
    # 评估
    evaluate_results(results, plot_roc=not args.no_plot)
