import { getAllArticles } from '@/lib/articles';
import ChannelNav from '@/components/ChannelNav';
import ArticleList from '@/components/ArticleList';

export default async function HomePage() {
    const allArticles = getAllArticles();

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

            {/* Channel Navigation */}
            <ChannelNav />

            {/* Articles List (Client Side Pagination) */}
            <ArticleList articles={allArticles} />
        </div>
    );
}
