import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronDown } from 'lucide-react';
import { EntityRecognition } from '@/lib/types';

interface EntityRecognitionCardProps {
    data: EntityRecognition;
}

export function EntityRecognitionCard({ data }: EntityRecognitionCardProps) {
    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>步骤1: 实体识别</span>
                    <Badge variant="outline" className="ml-2">
                        置信度: {(data.disease.confidence_score * 100).toFixed(0)}%
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 药品信息 */}
                <Collapsible defaultOpen>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">药品信息</span>
                            <Badge>{data.drug.name}</Badge>
                        </div>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-2 px-4">
                        <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                            <div>
                                <span className="text-sm font-medium">规格：</span>
                                <span className="text-sm text-muted-foreground">
                                    {data.drug.spec || '未指定'}
                                </span>
                            </div>
                            <div>
                                <span className="text-sm font-medium">分类：</span>
                                <div className="mt-1 flex flex-wrap gap-1">
                                    {data.drug.categories.map((cat, idx) => (
                                        <Badge key={idx} variant="secondary">
                                            {cat}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <span className="text-sm font-medium">适应症：</span>
                                <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
                                    {data.drug.indications.map((indication, idx) => (
                                        <li key={idx}>{indication}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </CollapsibleContent>
                </Collapsible>

                {/* 疾病信息 */}
                <Collapsible defaultOpen>
                    <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-muted/50">
                        <div className="flex items-center gap-2">
                            <span className="font-semibold">疾病信息</span>
                            <Badge variant="outline">{data.disease.name}</Badge>
                        </div>
                        <ChevronDown className="h-4 w-4 transition-transform duration-200 [&[data-state=open]]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-2 px-4">
                        <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                            {data.disease.attributes?.severity && (
                                <div>
                                    <span className="text-sm font-medium">严重程度：</span>
                                    <Badge variant="destructive" className="ml-2">
                                        {data.disease.attributes.severity}
                                    </Badge>
                                </div>
                            )}
                            {data.disease.sub_diseases && data.disease.sub_diseases.length > 0 && (
                                <div>
                                    <span className="text-sm font-medium">疾病组成：</span>
                                    <ul className="mt-1 space-y-1">
                                        {data.disease.sub_diseases.map((subDisease, idx) => (
                                            <li key={idx} className="flex items-center gap-2">
                                                <Badge
                                                    variant={
                                                        subDisease.type === 'primary'
                                                            ? 'default'
                                                            : 'secondary'
                                                    }
                                                >
                                                    {subDisease.type === 'primary' ? '原发' : '继发'}
                                                </Badge>
                                                <span className="text-sm">{subDisease.name}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </CollapsibleContent>
                </Collapsible>
            </CardContent>
        </Card>
    );
}
