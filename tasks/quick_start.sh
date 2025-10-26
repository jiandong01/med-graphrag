#!/bin/bash
# 疾病提取任务快速开始脚本

echo "=========================================="
echo "  疾病提取任务 - 快速开始"
echo "=========================================="
echo ""

# 检查环境
echo "1. 检查环境配置..."

# 检查 Elasticsearch
echo -n "   - Elasticsearch: "
if curl -s http://localhost:9200 > /dev/null 2>&1; then
    echo "✓ 运行中"
else
    echo "✗ 未运行"
    echo "   请先启动: make es up"
    exit 1
fi

# 检查 API Key
echo -n "   - DEEPSEEK_API_KEY: "
if grep -q "DEEPSEEK_API_KEY" .env 2>/dev/null; then
    echo "✓ 已配置"
else
    echo "✗ 未配置"
    echo ""
    echo "请配置 API Key:"
    echo "  echo 'DEEPSEEK_API_KEY=your_key' >> .env"
    exit 1
fi

echo ""
echo "2. 查看当前状态..."
python tasks/extract_diseases.py --status

echo ""
echo "=========================================="
echo "  选择运行模式:"
echo "=========================================="
echo "  1) 小规模测试 (10个药品)"
echo "  2) 中等规模 (100个药品)"
echo "  3) 正常处理 (batch-size=100, 全量)"
echo "  4) 快速处理 (batch-size=500, 全量)"
echo "  5) 从上次继续"
echo "  6) 查看帮助"
echo "  q) 退出"
echo ""
read -p "请选择 [1-6/q]: " choice

case $choice in
    1)
        echo ""
        echo "开始小规模测试..."
        python tasks/extract_diseases.py --batch-size 10 --start-from 0
        ;;
    2)
        echo ""
        echo "开始中等规模处理..."
        python tasks/extract_diseases.py --batch-size 100 --start-from 0
        ;;
    3)
        echo ""
        echo "开始正常处理..."
        echo "提示: 这将需要 2-3 天时间"
        read -p "确认继续? [y/N]: " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            nohup python tasks/extract_diseases.py --batch-size 100 > tasks/logs/extraction_run.log 2>&1 &
            echo "任务已在后台启动"
            echo "查看日志: tail -f tasks/logs/extraction_run.log"
            echo "查看进度: python tasks/extract_diseases.py --status"
        fi
        ;;
    4)
        echo ""
        echo "开始快速处理..."
        echo "提示: 这将需要 1-2 天时间"
        read -p "确认继续? [y/N]: " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            nohup python tasks/extract_diseases.py --batch-size 500 > tasks/logs/extraction_run.log 2>&1 &
            echo "任务已在后台启动"
            echo "查看日志: tail -f tasks/logs/extraction_run.log"
            echo "查看进度: python tasks/extract_diseases.py --status"
        fi
        ;;
    5)
        echo ""
        echo "从上次继续..."
        python tasks/extract_diseases.py --resume
        ;;
    6)
        python tasks/extract_diseases.py --help
        ;;
    q|Q)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac
