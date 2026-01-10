import Link from 'next/link';
import { getAllArticles } from '@/lib/articles';

export default function HomePage() {
    const articles = getAllArticles();

    return (
        <div className="max-w-5xl mx-auto px-4">
            {/* Hero */}
            <section className="text-center py-12 mb-8">
                <h1 className="font-display text-4xl md:text-5xl font-bold text-gray-800 mb-4">
                    YouTube Summarizer
                </h1>
                <p className="text-lg text-gray-600 max-w-xl mx-auto">
                    長いYouTube動画を、読みやすいブログ形式に要約しています。
                </p>
            </section>

            {/* Articles List */}
            {articles.length === 0 ? (
                <div className="text-center py-16 text-gray-500">
                    <p>まだ記事がありません。</p>
                    <p className="text-sm mt-2">
                        <code className="bg-gray-100 px-2 py-1 rounded">python scripts/process_video.py VIDEO_ID</code> で記事を生成してください。
                    </p>
                </div>
            ) : (
                <div className="flex flex-col gap-4">
                    {articles.map((article) => (
                        <Link
                            key={article.slug}
                            href={`/article/${article.slug}/`}
                            className="group flex flex-col md:flex-row gap-4 p-4 bg-white rounded-lg border border-gray-200 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
                        >
                            {/* Thumbnail */}
                            <div className="md:w-72 md:min-w-72 flex-shrink-0">
                                <img
                                    src={article.thumbnail}
                                    alt={article.title}
                                    className="w-full aspect-video object-cover rounded-md bg-gray-100"
                                />
                            </div>

                            {/* Content */}
                            <div className="flex-1 flex flex-col gap-1">
                                <span className="text-xs font-semibold text-forest uppercase tracking-wide">
                                    {article.channel}
                                </span>
                                <h2 className="font-display text-lg font-semibold text-gray-800 line-clamp-2 group-hover:text-coral transition-colors">
                                    {article.title}
                                </h2>
                                {article.excerpt && (
                                    <p className="text-sm text-gray-600 line-clamp-2 mt-1">
                                        {article.excerpt}
                                    </p>
                                )}
                                <span className="text-xs text-gray-400 mt-auto pt-2">
                                    {article.publishedAt
                                        ? new Date(article.publishedAt).toLocaleDateString('ja-JP')
                                        : ''}
                                </span>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
