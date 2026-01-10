import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

export interface TranscriptEntry {
    start: number;
    duration: number;
    text: string;
}

export interface Article {
    slug: string;
    title: string;
    videoId: string;
    channel: string;
    publishedAt: string;
    youtubeUrl: string;
    thumbnail: string;
    content: string;
    transcript: TranscriptEntry[] | null;
}

export interface ArticleMeta {
    slug: string;
    title: string;
    videoId: string;
    channel: string;
    publishedAt: string;
    thumbnail: string;
    excerpt: string; // 要約の冒頭部分
}

const summariesDirectory = path.join(process.cwd(), 'data/summaries');
const transcriptsDirectory = path.join(process.cwd(), 'data/transcripts');

/**
 * Get all article slugs for static generation
 */
export function getAllArticleSlugs(): string[] {
    try {
        const fileNames = fs.readdirSync(summariesDirectory);
        return fileNames
            .filter((fileName) => fileName.endsWith('.md'))
            .map((fileName) => fileName.replace(/\.md$/, ''));
    } catch (error) {
        console.error('Error reading summaries directory:', error);
        return [];
    }
}

/**
 * Get all articles metadata for listing
 */
export function getAllArticles(): ArticleMeta[] {
    const slugs = getAllArticleSlugs();

    const articles = slugs.map((slug) => {
        const fullPath = path.join(summariesDirectory, `${slug}.md`);
        const fileContents = fs.readFileSync(fullPath, 'utf8');
        const { data, content } = matter(fileContents);

        // 要約の冒頭部分を抽出（最初の段落、最大200文字）
        const firstParagraph = content
            .split('\n\n')
            .find(p => p.trim() && !p.startsWith('#') && !p.startsWith('-') && !p.startsWith('```'));
        const excerpt = firstParagraph
            ? firstParagraph.replace(/\*\*/g, '').substring(0, 200) + (firstParagraph.length > 200 ? '...' : '')
            : '';

        return {
            slug,
            title: data.title || 'Untitled',
            videoId: data.video_id || slug,
            channel: data.channel || 'Unknown',
            publishedAt: data.published_at || '',
            thumbnail: data.thumbnail || `https://img.youtube.com/vi/${data.video_id || slug}/hqdefault.jpg`,
            excerpt,
        };
    });

    // Sort by published date (newest first)
    return articles.sort((a, b) => {
        if (a.publishedAt < b.publishedAt) return 1;
        if (a.publishedAt > b.publishedAt) return -1;
        return 0;
    });
}

/**
 * Get a single article by slug
 */
export function getArticleBySlug(slug: string): Article | null {
    try {
        const fullPath = path.join(summariesDirectory, `${slug}.md`);
        const fileContents = fs.readFileSync(fullPath, 'utf8');
        const { data, content } = matter(fileContents);

        // Load transcript if available
        let transcript: TranscriptEntry[] | null = null;
        try {
            const transcriptPath = path.join(transcriptsDirectory, `${slug}.json`);
            const transcriptContents = fs.readFileSync(transcriptPath, 'utf8');
            const transcriptData = JSON.parse(transcriptContents);
            transcript = transcriptData.transcript || null;
        } catch {
            // Transcript not available
        }

        return {
            slug,
            title: data.title || 'Untitled',
            videoId: data.video_id || slug,
            channel: data.channel || 'Unknown',
            publishedAt: data.published_at || '',
            youtubeUrl: data.youtube_url || `https://www.youtube.com/watch?v=${data.video_id || slug}`,
            thumbnail: data.thumbnail || `https://img.youtube.com/vi/${data.video_id || slug}/hqdefault.jpg`,
            content,
            transcript,
        };
    } catch (error) {
        console.error(`Error reading article ${slug}:`, error);
        return null;
    }
}

/**
 * Get unique channels for filtering
 */
export function getAllChannels(): string[] {
    const articles = getAllArticles();
    const channels = [...new Set(articles.map((a) => a.channel))];
    return channels.sort();
}
