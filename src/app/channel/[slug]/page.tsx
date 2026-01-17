import { notFound } from 'next/navigation';
import {
    getAllChannelSlugs,
    slugToChannel,
    getArticlesByChannel,
    channelToSlug
} from '@/lib/articles';
import ArticleList from '@/components/ArticleList';
import Link from 'next/link';

interface ChannelPageProps {
    params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
    const slugs = getAllChannelSlugs();
    return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: ChannelPageProps) {
    const { slug } = await params;
    const channel = slugToChannel(slug);

    if (!channel) {
        return { title: 'チャンネルが見つかりません' };
    }

    return {
        title: `${channel} | YouTube Summarizer`,
        description: `${channel}の動画要約一覧`,
    };
}

export default async function ChannelPage({ params }: ChannelPageProps) {
    const { slug } = await params;
    const channel = slugToChannel(slug);

    if (!channel) {
        notFound();
    }

    const articles = getArticlesByChannel(channel);

    return (
        <div className="max-w-5xl mx-auto px-4 pb-12">
            {/* Breadcrumb */}
            <nav className="mb-6 text-sm text-gray-500">
                <Link href="/" className="hover:text-coral">ホーム</Link>
                <span className="mx-2">›</span>
                <span className="text-gray-800">{channel}</span>
            </nav>

            {/* Channel Header */}
            <section className="mb-8">
                <h1 className="font-display text-3xl md:text-4xl font-bold text-gray-800 mb-2">
                    {channel}
                </h1>
                <p className="text-gray-600">
                    {articles.length}件の記事
                </p>
            </section>

            {/* Articles List */}
            <ArticleList articles={articles} />
        </div>
    );
}
