import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronDown, AlertTriangle, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { FinalResult } from '@/lib/types';

interface FinalResultCardProps {
    data: FinalResult;
}

export function FinalResultCard({ data }: FinalResultCardProps) {
    const getCategoryIcon = () => {
        const category = data.final_judgment.category;
        if (category.includes('标准用药') || category.includes('符合说明书')) {
            return <CheckCircle2 className="h-6 w-6 text-green-500" />;
        }
        if (category.includes('合理超说明书') || category.includes('可考虑')) {
            return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
        }
        return <XCircle className="h-6 w-6 text-red-500" />;
    };

    const getCategoryVariant = () => {
        const category = data.final_judgment.category;
        if (category.includes('标准用药') || category.includes('符合说明书')) {
            return 'default';
        }
        if (category.includes('合理超说明书') || category.includes('可考虑')) {
            return 'secondary';
        }
        return 'destructive';
    };

    return (
        <Card className="w-full border-2">
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>最终判断结果</span>
                    <Badge variant="outline" className="ml-2">
                        置信度: {(data.final_judgment.confidence * 100).toFixed(0)}%
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 判断结论 */}
                <div className="rounded-lg border-2 p-4 bg-background">
                    <div className="flex items-center gap-3 mb-3">
                        {getCategoryIcon()}
                        <div>
                            <span className="text-sm text-muted-foreground">用药类别</span>
                            <div className="mt-1">
                                <Badge variant={getCategoryVariant()} className="text-base px-3 py-1">
                                    {data.final_judgment.category}
                                </Badge>
                            </div>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div>
                            <span className="text-sm font-medium">判断说明：</span>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {data.final_judgment.explanation}
                            </p>
                        </div>
                        <div>
                            <span className="text-sm font-medium">临床建议：</span>
                            <p className="mt-1 text-sm text-muted-foreground whitespace-pre-line">
                                {data.final_judgment.recommendation}
                            </p>
                        </div>
                    </div>
                </div>

                {/* 综合评分 */}
                <Collapsible defaultOpen>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <span className="font-semibold">综合评分</span>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-2 px-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="rounded-lg bg-muted/50 p-3">
                                <div className="text-xs text-muted-foreground mb-1">
                                    适应症匹配度
                                </div>
                                <div className="flex items-center gap-2">
                                    <Badge variant="secondary">
                                        {(data.summary.indication_match.confidence * 100).toFixed(0)}%
                                    </Badge>
                                    <span className="text-xs">{data.summary.indication_match.result}</span>
                                </div>
                            </div>
                            <div className="rounded-lg bg-muted/50 p-3">
                                <div className="text-xs text-muted-foreground mb-1">
                                    机制相似度
                                </div>
                                <Badge variant="secondary">
                                    {(data.summary.similarity_score * 100).toFixed(0)}%
                                </Badge>
                            </div>
                            <div className="rounded-lg bg-muted/50 p-3">
                                <div className="text-xs text-muted-foreground mb-1">证据强度</div>
                                <Badge variant="secondary">
                                    {(data.summary.evidence_strength * 100).toFixed(0)}%
                                </Badge>
                            </div>
                            <div className="rounded-lg bg-muted/50 p-3">
                                <div className="text-xs text-muted-foreground mb-1">
                                    获益风险比
                                </div>
                                <Badge
                                    variant={
                                        data.summary.benefit_risk_ratio >= 0.7
                                            ? 'default'
                                            : data.summary.benefit_risk_ratio >= 0.5
                                              ? 'secondary'
                                              : 'destructive'
                                    }
                                >
                                    {(data.summary.benefit_risk_ratio * 100).toFixed(0)}%
                                </Badge>
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                            {data.summary.indication_match.notes}
                        </div>
                    </CollapsibleContent>
                </Collapsible>

                {/* 监测计划 */}
                {data.monitoring_plan && (
                    <Collapsible>
                        <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                            <div className="flex items-center gap-2">
                                <Clock className="h-4 w-4" />
                                <span className="font-semibold">监测计划</span>
                            </div>
                            <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-3 px-4">
                            {/* 疗效指标 */}
                            <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                                <span className="text-sm font-medium">疗效监测指标：</span>
                                <ul className="list-inside list-disc text-sm text-muted-foreground">
                                    {data.monitoring_plan.efficacy_indicators.map((indicator, idx) => (
                                        <li key={idx}>{indicator}</li>
                                    ))}
                                </ul>
                            </div>

                            {/* 安全性监测 */}
                            <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                                <span className="text-sm font-medium">安全性监测：</span>
                                <ul className="list-inside list-disc text-sm text-muted-foreground">
                                    {data.monitoring_plan.safety_monitoring.map((item, idx) => (
                                        <li key={idx}>{item}</li>
                                    ))}
                                </ul>
                            </div>

                            {/* 随访计划 */}
                            <div className="rounded-lg bg-blue-50 p-3">
                                <span className="text-sm font-medium">随访计划：</span>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    {data.monitoring_plan.follow_up_schedule}
                                </p>
                            </div>

                            {/* 调整标准 */}
                            <div className="space-y-2">
                                <span className="text-sm font-medium">剂量调整标准：</span>
                                <div className="rounded-lg bg-yellow-50 p-3">
                                    <div className="text-xs font-medium text-yellow-800 mb-1">
                                        减量指征：
                                    </div>
                                    <ul className="list-inside list-disc text-xs text-yellow-700">
                                        {data.monitoring_plan.adjustment_criteria.dose_reduction.map(
                                            (criteria, idx) => (
                                                <li key={idx}>{criteria}</li>
                                            )
                                        )}
                                    </ul>
                                </div>
                                <div className="rounded-lg bg-red-50 p-3">
                                    <div className="text-xs font-medium text-red-800 mb-1">
                                        停药指征：
                                    </div>
                                    <ul className="list-inside list-disc text-xs text-red-700">
                                        {data.monitoring_plan.adjustment_criteria.discontinuation.map(
                                            (criteria, idx) => (
                                                <li key={idx}>{criteria}</li>
                                            )
                                        )}
                                    </ul>
                                </div>
                            </div>
                        </CollapsibleContent>
                    </Collapsible>
                )}
            </CardContent>
        </Card>
    );
}
