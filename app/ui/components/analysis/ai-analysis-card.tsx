import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronDown, TrendingUp, TrendingDown } from 'lucide-react';
import { Analysis } from '@/lib/types';

interface AIAnalysisCardProps {
    data: Analysis;
}

export function AIAnalysisCard({ data }: AIAnalysisCardProps) {
    const avgScore =
        (data.similarity_analysis.mechanism.score +
            data.similarity_analysis.clinical.score) /
        2;

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>步骤3: AI辅助分析</span>
                    <Badge variant="outline" className="ml-2">
                        综合评分: {(avgScore * 100).toFixed(0)}%
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 相似度分析 */}
                <Collapsible defaultOpen>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">相似度分析</span>
                        </div>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-3 px-4">
                        {/* 机制相似度 */}
                        <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">机制相似度</span>
                                <Badge variant="secondary">
                                    {(data.similarity_analysis.mechanism.score * 100).toFixed(0)}%
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                {data.similarity_analysis.mechanism.explanation}
                            </p>
                        </div>

                        {/* 临床相似度 */}
                        <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">临床相似度</span>
                                <Badge variant="secondary">
                                    {(data.similarity_analysis.clinical.score * 100).toFixed(0)}%
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                {data.similarity_analysis.clinical.explanation}
                            </p>
                        </div>
                    </CollapsibleContent>
                </Collapsible>

                {/* 证据分析 */}
                <Collapsible>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">证据分析</span>
                            <Badge variant="outline">
                                {data.evidence_analysis.clinical_guidelines &&
                                data.evidence_analysis.expert_consensus
                                    ? '3项证据'
                                    : data.evidence_analysis.clinical_guidelines ||
                                        data.evidence_analysis.expert_consensus
                                      ? '2项证据'
                                      : '1项证据'}
                            </Badge>
                        </div>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-3 px-4">
                        {/* 药品说明书 */}
                        <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">药品说明书</span>
                                <Badge variant="secondary">
                                    置信度: {(data.evidence_analysis.drug_label.confidence * 100).toFixed(0)}%
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                {data.evidence_analysis.drug_label.content}
                            </p>
                        </div>

                        {/* 临床指南 */}
                        {data.evidence_analysis.clinical_guidelines && (
                            <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">临床指南</span>
                                    <Badge variant="secondary">
                                        置信度:{' '}
                                        {(
                                            data.evidence_analysis.clinical_guidelines.confidence *
                                            100
                                        ).toFixed(0)}
                                        %
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {data.evidence_analysis.clinical_guidelines.content}
                                </p>
                            </div>
                        )}

                        {/* 专家共识 */}
                        {data.evidence_analysis.expert_consensus && (
                            <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium">专家共识</span>
                                    <Badge variant="secondary">
                                        置信度:{' '}
                                        {(
                                            data.evidence_analysis.expert_consensus.confidence * 100
                                        ).toFixed(0)}
                                        %
                                    </Badge>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {data.evidence_analysis.expert_consensus.content}
                                </p>
                            </div>
                        )}
                    </CollapsibleContent>
                </Collapsible>

                {/* 风险评估 */}
                <Collapsible>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">获益风险比</span>
                            <Badge
                                variant={
                                    data.risk_assessment.benefit_risk_ratio >= 0.7
                                        ? 'default'
                                        : data.risk_assessment.benefit_risk_ratio >= 0.5
                                          ? 'secondary'
                                          : 'destructive'
                                }
                            >
                                {(data.risk_assessment.benefit_risk_ratio * 100).toFixed(0)}%
                            </Badge>
                        </div>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-3 px-4">
                        {/* 获益因素 */}
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <TrendingUp className="h-4 w-4 text-green-500" />
                                <span className="text-sm font-medium">获益因素</span>
                            </div>
                            {data.risk_assessment.benefit_factors.map((benefit, idx) => (
                                <div key={idx} className="rounded-lg bg-green-50 p-3 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium">{benefit.factor}</span>
                                        <Badge variant="outline">
                                            {(benefit.score * 100).toFixed(0)}%
                                        </Badge>
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        {benefit.evidence}
                                    </p>
                                </div>
                            ))}
                        </div>

                        {/* 风险因素 */}
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <TrendingDown className="h-4 w-4 text-red-500" />
                                <span className="text-sm font-medium">风险因素</span>
                            </div>
                            {data.risk_assessment.risk_factors.map((risk, idx) => (
                                <div key={idx} className="rounded-lg bg-red-50 p-3 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium">{risk.factor}</span>
                                        <Badge variant="outline">
                                            {(risk.score * 100).toFixed(0)}%
                                        </Badge>
                                    </div>
                                    <p className="text-sm text-muted-foreground">{risk.evidence}</p>
                                </div>
                            ))}
                        </div>
                    </CollapsibleContent>
                </Collapsible>
            </CardContent>
        </Card>
    );
}
