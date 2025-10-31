'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Pill, Activity } from 'lucide-react';
import { EntityRecognitionCard } from '@/components/analysis/entity-recognition-card';
import { IndicationAnalysisCard } from '@/components/analysis/indication-analysis-card';
import { AIAnalysisCard } from '@/components/analysis/ai-analysis-card';
import { FinalResultCard } from '@/components/analysis/final-result-card';
import type { AnalysisResponse } from '@/lib/types';

export default function Home() {
    const [drugName, setDrugName] = useState('');
    const [diseaseName, setDiseaseName] = useState('');
    const [description, setDescription] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<AnalysisResponse | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);
        setResult(null);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    drug_name: drugName,
                    disease_name: diseaseName,
                    description: description,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '分析失败');
            }

            const data = await response.json();
            // 后端返回格式: { success: true, data: {...}, timestamp: "..." }
            // 我们需要提取 data 字段
            setResult(data.data || data);
        } catch (err) {
            setError(err instanceof Error ? err.message : '分析过程中发生错误');
        } finally {
            setIsLoading(false);
        }
    };

    const handleReset = () => {
        setDrugName('');
        setDiseaseName('');
        setDescription('');
        setResult(null);
        setError(null);
    };

    return (
        <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900">
            <div className="container mx-auto px-4 py-8 max-w-6xl">
                {/* 页面标题 */}
                <div className="mb-8 text-center">
                    <div className="flex items-center justify-center gap-3 mb-3">
                        <Activity className="h-10 w-10 text-primary" />
                        <h1 className="text-4xl font-bold tracking-tight">
                            医疗超适应症智能分析系统
                        </h1>
                    </div>
                    <p className="text-muted-foreground text-lg">
                        基于大语言模型和知识图谱的超适应症用药智能判断与决策支持
                    </p>
                </div>

                {/* 输入表单 */}
                <Card className="mb-8">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Pill className="h-5 w-5" />
                            用药信息输入
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="drug">药品名称 *</Label>
                                    <Input
                                        id="drug"
                                        placeholder="例如: 美托洛尔、阿司匹林"
                                        value={drugName}
                                        onChange={(e) => setDrugName(e.target.value)}
                                        required
                                        disabled={isLoading}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="disease">疾病名称 *</Label>
                                    <Input
                                        id="disease"
                                        placeholder="例如: 心力衰竭、高血压"
                                        value={diseaseName}
                                        onChange={(e) => setDiseaseName(e.target.value)}
                                        required
                                        disabled={isLoading}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="description">临床描述（可选）</Label>
                                <Input
                                    id="description"
                                    placeholder="例如: 患者诊断为心力衰竭，拟使用美托洛尔治疗"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    disabled={isLoading}
                                />
                            </div>
                            <div className="flex gap-3">
                                <Button type="submit" disabled={isLoading} className="flex-1">
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            分析中...
                                        </>
                                    ) : (
                                        '开始分析'
                                    )}
                                </Button>
                                {result && (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={handleReset}
                                        disabled={isLoading}
                                    >
                                        重新分析
                                    </Button>
                                )}
                            </div>
                        </form>
                    </CardContent>
                </Card>

                {/* 错误提示 */}
                {error && (
                    <Card className="mb-8 border-destructive">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-2 text-destructive">
                                <Badge variant="destructive">错误</Badge>
                                <span>{error}</span>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* 分析结果 */}
                {result && (
                    <div className="space-y-6">
                        {/* 分析流程标题 */}
                        <div className="text-center">
                            <h2 className="text-2xl font-bold mb-2">分析流程与结果</h2>
                            <p className="text-muted-foreground">
                                系统将通过4个步骤完成超适应症用药的智能分析
                            </p>
                        </div>

                        {/* 实体识别 */}
                        {result.entity_recognition && (
                            <EntityRecognitionCard data={result.entity_recognition} />
                        )}

                        {/* 规则判断 */}
                        {result.indication_analysis && (
                            <IndicationAnalysisCard data={result.indication_analysis} />
                        )}

                        {/* AI辅助分析 */}
                        {result.analysis && <AIAnalysisCard data={result.analysis} />}

                        {/* 最终结果 */}
                        {result.final_result && <FinalResultCard data={result.final_result} />}

                        {/* 分析会话信息 */}
                        {result.final_result?.analysis_session && (
                            <Card>
                                <CardContent className="pt-6">
                                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                                        <span>会话ID: {result.final_result.analysis_session.id}</span>
                                        <span>
                                            分析时间:{' '}
                                            {new Date(
                                                result.final_result.analysis_session.timestamp
                                            ).toLocaleString('zh-CN')}
                                        </span>
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                )}

                {/* 页脚说明 */}
                {!result && !isLoading && (
                    <Card className="mt-8 bg-muted/50">
                        <CardContent className="pt-6">
                            <div className="space-y-3 text-sm text-muted-foreground">
                                <p className="font-medium text-foreground">系统功能说明：</p>
                                <ul className="list-disc list-inside space-y-1">
                                    <li>
                                        <strong>实体识别：</strong>
                                        准确识别药品和疾病信息，从知识库获取详细资料
                                    </li>
                                    <li>
                                        <strong>规则判断：</strong>
                                        基于药品说明书进行精确的适应症匹配和禁忌症检查
                                    </li>
                                    <li>
                                        <strong>AI辅助分析：</strong>
                                        通过机制相似度、临床证据和风险评估提供智能建议
                                    </li>
                                    <li>
                                        <strong>综合决策：</strong>
                                        整合规则判断和AI分析，给出明确的用药建议和监测方案
                                    </li>
                                </ul>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}
