import Link from 'next/link';
import { getAllArticles } from '@/lib/articles';

export default async function HomePage({
    searchParams,
}: {
    searchParams: Promise<{ page?: string }>;
}) {
    const params = await searchParams;
    const currentPage = parseInt(params.page || '1', 10);
    const articlesPerPage = 20;

    const allArticles = getAllArticles();
    const totalArticles = allArticles.length;
    const totalPages = Math.ceil(totalArticles / articlesPerPage);

    // Get current page articles
    const startIndex = (currentPage - 1) * articlesPerPage;
    const paginatedArticles = allArticles.slice(startIndex, startIndex + articlesPerPage);

    // Group articles by date
    const articlesByDate: Record<string, typeof paginatedArticles> = {};
    paginatedArticles.forEach((article) => {
        const date = article.publishedAt || 'Unknown Date';
        if (!articlesByDate[date]) {
            articlesByDate[date] = [];
        }
        articlesByDate[date].push(article);
    });

    // Sort dates (newest first)
    const sortedDates = Object.keys(articlesByDate).sort((a, b) => (a < b ? 1 : -1));

    const formatDate = (dateStr: string) => {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('ja-JP', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="max-w-5xl mx-auto px-4 pb-12">
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
            {totalArticles === 0 ? (
                <div className="text-center py-16 text-gray-500">
                    <p>まだ記事がありません。</p>
                    <p className="text-sm mt-2">
                        <code className="bg-gray-100 px-2 py-1 rounded">python scripts/process_video.py VIDEO_ID</code> で記事を生成してください。
                    </p>
                </div>
            ) : (
                <div className="flex flex-col gap-10">
                    {sortedDates.map((date) => (
                        <div key={date} className="flex flex-col gap-6">
                            <h3 className="text-xl font-bold text-gray-800 border-l-4 border-coral pl-4">
                                {formatDate(date)}
                            </h3>
                            <div className="flex flex-col gap-4">
                                {articlesByDate[date].map((article) => (
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
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    ))}

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <nav className="flex justify-center gap-2 mt-8">
                            {currentPage > 1 && (
                                <Link
                                    href={`/?page=${currentPage - 1}`}
                                    className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                                >
                                    前のページ
                                </Link>
                            )}
                            <div className="flex items-center gap-1">
                                {[...Array(totalPages)].map((_, i) => (
                                    <Link
                                        key={i + 1}
                                        href={`/?page=${i + 1}`}
                                        className={`px-4 py-2 text-sm font-medium rounded-md ${currentPage === i + 1
                                            ? 'bg-coral text-white'
                                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                                            }`}
                                    >
                                        {i + 1}
                                    </Link>
                                ))}
                            </div>
                            {currentPage < totalPages && (
                                <Link
                                    href={`/?page=${currentPage + 1}`}
                                    className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                                >
                                    次のページ
                                </Link>
                            )}
                        </nav>
                    )}
                </div>
            )}
        </div>
    );
}
