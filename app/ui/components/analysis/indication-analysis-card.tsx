import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronDown, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { IndicationAnalysis } from '@/lib/types';

interface IndicationAnalysisCardProps {
    data: IndicationAnalysis;
}

export function IndicationAnalysisCard({ data }: IndicationAnalysisCardProps) {
    const getMatchIcon = () => {
        const result = data.indication_match.result;
        if (result.includes('完全匹配') || result.includes('精确匹配')) {
            return <CheckCircle2 className="h-5 w-5 text-green-500" />;
        }
        if (result.includes('部分匹配')) {
            return <AlertCircle className="h-5 w-5 text-yellow-500" />;
        }
        return <XCircle className="h-5 w-5 text-red-500" />;
    };

    const getMatchVariant = () => {
        const result = data.indication_match.result;
        if (result.includes('完全匹配') || result.includes('精确匹配')) {
            return 'default';
        }
        if (result.includes('部分匹配')) {
            return 'secondary';
        }
        return 'destructive';
    };

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>步骤2: 规则判断</span>
                    <Badge variant="outline" className="ml-2">
                        置信度: {(data.indication_match.confidence * 100).toFixed(0)}%
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 适应症匹配 */}
                <Collapsible defaultOpen>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <div className="flex items-center gap-2">
                            {getMatchIcon()}
                            <span className="font-semibold">适应症匹配</span>
                            <Badge variant={getMatchVariant()}>
                                {data.indication_match.result}
                            </Badge>
                        </div>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-2 px-4">
                        <div className="rounded-lg bg-muted/50 p-3 space-y-3">
                            {data.indication_match.matched_indications.length > 0 && (
                                <div>
                                    <span className="text-sm font-medium">匹配的适应症：</span>
                                    <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
                                        {data.indication_match.matched_indications.map(
                                            (indication, idx) => (
                                                <li key={idx}>{indication}</li>
                                            )
                                        )}
                                    </ul>
                                </div>
                            )}
                            <div>
                                <span className="text-sm font-medium">说明：</span>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    {data.indication_match.explanation}
                                </p>
                            </div>
                        </div>
                    </CollapsibleContent>
                </Collapsible>

                {/* 禁忌症检查 */}
                {data.contraindication_check && (
                    <Collapsible>
                        <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                            <div className="flex items-center gap-2">
                                {data.contraindication_check.has_contraindications ? (
                                    <XCircle className="h-5 w-5 text-red-500" />
                                ) : (
                                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                                )}
                                <span className="font-semibold">禁忌症检查</span>
                                <Badge
                                    variant={
                                        data.contraindication_check.has_contraindications
                                            ? 'destructive'
                                            : 'default'
                                    }
                                >
                                    {data.contraindication_check.has_contraindications
                                        ? '存在禁忌'
                                        : '无禁忌'}
                                </Badge>
                            </div>
                            <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-2 px-4">
                            <div className="rounded-lg bg-muted/50 p-3 space-y-3">
                                {data.contraindication_check.matched_contraindications &&
                                    data.contraindication_check.matched_contraindications.length >
                                        0 && (
                                        <div>
                                            <span className="text-sm font-medium">
                                                匹配的禁忌症：
                                            </span>
                                            <ul className="mt-1 list-inside list-disc text-sm text-destructive">
                                                {data.contraindication_check.matched_contraindications.map(
                                                    (contraindication, idx) => (
                                                        <li key={idx}>{contraindication}</li>
                                                    )
                                                )}
                                            </ul>
                                        </div>
                                    )}
                                {data.contraindication_check.explanation && (
                                    <div>
                                        <span className="text-sm font-medium">说明：</span>
                                        <p className="mt-1 text-sm text-muted-foreground">
                                            {data.contraindication_check.explanation}
                                        </p>
                                    </div>
                                )}
                            </div>
                        </CollapsibleContent>
                    </Collapsible>
                )}
            </CardContent>
        </Card>
    );
}
