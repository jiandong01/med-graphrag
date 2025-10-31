import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { drug_name, disease_name, description } = body;

        if (!drug_name || !disease_name) {
            return NextResponse.json(
                { error: '药品名称和疾病名称不能为空' },
                { status: 400 }
            );
        }

        // 转换为后端API期望的格式
        const apiRequest = {
            patient: {
                diagnosis: disease_name,
                medical_history: description || undefined,
            },
            prescription: {
                drug_name: drug_name,
            },
            clinical_context: description || undefined,
        };

        // 调用Python后端API
        const response = await fetch('http://localhost:8000/api/v1/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(apiRequest),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return NextResponse.json(
                { error: errorData.detail || '后端服务请求失败' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Analysis API error:', error);
        return NextResponse.json(
            { error: '服务器内部错误' },
            { status: 500 }
        );
    }
}
