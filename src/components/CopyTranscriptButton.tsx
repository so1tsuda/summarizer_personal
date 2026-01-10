'use client';

import { useState } from 'react';

interface TranscriptEntry {
    start: number;
    duration: number;
    text: string;
}

interface CopyTranscriptButtonProps {
    transcript: TranscriptEntry[];
}

export default function CopyTranscriptButton({ transcript }: CopyTranscriptButtonProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        const textToCopy = transcript.map(entry => {
            const minutes = Math.floor(entry.start / 60);
            const seconds = Math.floor(entry.start % 60);
            const timestamp = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            return `[${timestamp}] ${entry.text}`;
        }).join('\n');

        try {
            await navigator.clipboard.writeText(textToCopy);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
            alert('コピーに失敗しました。');
        }
    };

    return (
        <button
            onClick={handleCopy}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200 ${copied
                    ? 'bg-green-100 text-green-700'
                    : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
        >
            {copied ? (
                <>
                    <span>✅ コピーしました</span>
                </>
            ) : (
                <>
                    <span>📋 文字起こしをコピー</span>
                </>
            )}
        </button>
    );
}
