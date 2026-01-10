import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
    title: "YouTube Summarizer",
    description: "長いYouTube動画を読みやすく要約",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="ja">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;600;700&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="min-h-screen bg-gray-50 font-sans">
                {/* Header */}
                <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-200">
                    <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
                        <a href="/" className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors flex items-center gap-2">
                            <span className="text-2xl">📺</span>
                            <span>YouTube Summarizer</span>
                        </a>
                        <nav className="hidden md:flex gap-6">
                            <a href="/" className="text-gray-600 hover:text-blue-600 transition-colors font-medium">ホーム</a>
                        </nav>
                    </div>
                </header>

                {/* Main */}
                <main className="py-8">
                    {children}
                </main>

                {/* Footer */}
                <footer className="text-center py-8 border-t border-gray-200 text-gray-500 text-sm bg-white">
                    <div className="max-w-6xl mx-auto px-4">
                        <p>© 2026 YouTube Summarizer. Personal Use Only.</p>
                    </div>
                </footer>
            </body>
        </html>
    );
}
