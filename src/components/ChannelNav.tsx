import Link from 'next/link';
import { getAllChannels, channelToSlug } from '@/lib/articles';

interface ChannelNavProps {
    currentChannel?: string;
}

export default function ChannelNav({ currentChannel }: ChannelNavProps) {
    const channels = getAllChannels();

    return (
        <nav className="mb-10">
            <h2 className="text-lg font-bold text-gray-700 mb-4 text-center">📺 チャンネル別に見る</h2>
            <div className="grid grid-cols-2 gap-3 max-w-2xl mx-auto">
                {channels.map((channel) => (
                    <Link
                        key={channel}
                        href={`/channel/${channelToSlug(channel)}/`}
                        className={`
                            relative overflow-hidden
                            px-5 py-4 rounded-xl text-base font-semibold
                            text-center transition-all duration-300
                            ${currentChannel === channel
                                ? 'bg-gradient-to-r from-coral to-orange-400 text-white shadow-lg shadow-coral/30'
                                : 'bg-white text-gray-700 border border-gray-200 hover:border-coral/50 hover:shadow-md hover:shadow-coral/10 hover:-translate-y-0.5'
                            }
                        `}
                    >
                        <span className="relative z-10">{channel}</span>
                        {currentChannel !== channel && (
                            <div className="absolute inset-0 bg-gradient-to-r from-coral/5 to-orange-400/5 opacity-0 hover:opacity-100 transition-opacity" />
                        )}
                    </Link>
                ))}
            </div>
        </nav>
    );
}
