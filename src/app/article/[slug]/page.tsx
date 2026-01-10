import { notFound } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getAllArticleSlugs, getArticleBySlug } from '@/lib/articles';
import CopyTranscriptButton from '@/components/CopyTranscriptButton';

interface PageProps {
    params: Promise<{
        slug: string;
    }>;
}

export async function generateStaticParams() {
    const slugs = getAllArticleSlugs();
    return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: PageProps) {
    const { slug } = await params;
    const article = getArticleBySlug(slug);

    if (!article) {
        return { title: 'Not Found' };
    }

    return {
        title: `${article.title} | YouTube Summarizer`,
        description: `${article.channel}の動画「${article.title}」の要約`,
    };
}

export default async function ArticlePage({ params }: PageProps) {
    const { slug } = await params;
    const article = getArticleBySlug(slug);

    if (!article) {
        notFound();
    }

    return (
        <article className="max-w-3xl mx-auto px-4 py-8">
            {/* YouTube Embed */}
            <div className="mb-8 rounded-xl overflow-hidden shadow-xl bg-black aspect-video">
                <iframe
                    src={`https://www.youtube.com/embed/${article.videoId}`}
                    title={article.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                    className="w-full h-full border-0"
                ></iframe>
            </div>

            {/* Header */}
            <header className="mb-10">
                <span className="text-sm font-semibold text-emerald-600 uppercase tracking-wide">
                    {article.channel}
                </span>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mt-2 mb-4 leading-tight">
                    {article.title}
                </h1>
                <div className="flex items-center gap-4 text-gray-500 text-sm">
                    <span>
                        {article.publishedAt
                            ? new Date(article.publishedAt).toLocaleDateString('ja-JP', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                            })
                            : ''}
                    </span>
                </div>
                <a
                    href={article.youtubeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-500 text-white rounded-lg font-semibold mt-6 hover:bg-red-600 transition-colors shadow-md text-sm md:text-base"
                >
                    ▶ YouTubeで視聴
                </a>
            </header>

            {/* Content */}
            <div className="article-content">
                <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                        h1: ({ children }) => (
                            <h1 className="text-2xl font-bold text-gray-900 mt-10 mb-4 pb-2 border-b border-gray-200">
                                {children}
                            </h1>
                        ),
                        h2: ({ children }) => (
                            <h2 className="text-xl font-bold text-gray-900 mt-8 mb-4 pb-2 border-b border-gray-200">
                                {children}
                            </h2>
                        ),
                        h3: ({ children }) => (
                            <h3 className="text-lg font-bold text-gray-800 mt-6 mb-3">
                                {children}
                            </h3>
                        ),
                        p: ({ children }) => (
                            <p className="text-gray-700 leading-relaxed mb-4 text-lg">
                                {children}
                            </p>
                        ),
                        ul: ({ children }) => (
                            <ul className="list-disc list-inside space-y-2 mb-4 text-gray-700">
                                {children}
                            </ul>
                        ),
                        ol: ({ children }) => (
                            <ol className="list-decimal list-inside space-y-2 mb-4 text-gray-700">
                                {children}
                            </ol>
                        ),
                        li: ({ children }) => (
                            <li className="leading-relaxed">{children}</li>
                        ),
                        strong: ({ children }) => (
                            <strong className="font-bold text-gray-900">{children}</strong>
                        ),
                        blockquote: ({ children }) => (
                            <blockquote className="border-l-4 border-emerald-500 pl-4 my-4 italic text-gray-600">
                                {children}
                            </blockquote>
                        ),
                        hr: () => <hr className="my-8 border-gray-200" />,
                        a: ({ href, children }) => (
                            <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
                                {children}
                            </a>
                        ),
                    }}
                >
                    {article.content}
                </ReactMarkdown>
            </div>

            {/* Transcript Section */}
            {article.transcript && article.transcript.length > 0 && (
                <section className="mt-16 pt-8 border-t border-gray-200">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            📝 文字起こし
                        </h2>
                        <CopyTranscriptButton transcript={article.transcript} />
                    </div>
                    <div className="bg-gray-50 rounded-xl p-6 max-h-[600px] overflow-y-auto shadow-inner border border-gray-100">
                        <div className="space-y-3 text-sm text-gray-700 leading-relaxed">
                            {article.transcript.map((entry, index) => {
                                const minutes = Math.floor(entry.start / 60);
                                const seconds = Math.floor(entry.start % 60);
                                const timestamp = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                                return (
                                    <p key={index} className="flex gap-3 hover:bg-gray-100/50 p-1 -m-1 rounded transition-colors group">
                                        <span className="text-gray-400 font-mono text-xs min-w-[45px] pt-0.5 group-hover:text-gray-600">
                                            {timestamp}
                                        </span>
                                        <span>{entry.text}</span>
                                    </p>
                                );
                            })}
                        </div>
                    </div>
                </section>
            )}
        </article>
    );
}
