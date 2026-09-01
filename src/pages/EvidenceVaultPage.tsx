import React, { useState, useEffect } from 'react';
import { ClayCard } from '../components/ui/ClayCard';
import { PlatformBadge } from '../components/ui/PlatformBadge';
import { ConfidenceBadge } from '../components/ui/ConfidenceBadge';
import { EvidenceDrawer } from '../components/evidence/EvidenceDrawer';
import { MOCK_EVENTS } from '../services/mockData';
import { getAllEvents } from '../services/api';
import type { SocialEventItem } from '../services/api';
import { FileCheck, Search, Filter, ExternalLink, Code2, Eye, Forward, MessageSquare, RefreshCw } from 'lucide-react';
import { CanonicalSocialEvent } from '../types';

export const EvidenceVaultPage: React.FC = () => {
  const [selectedEvent, setSelectedEvent] = useState<CanonicalSocialEvent | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Real collected Telegram events
  const [telegramEvents, setTelegramEvents] = useState<SocialEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch real events from backend on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await getAllEvents(200);
        if (!cancelled) {
          setTelegramEvents(result.items || []);
        }
      } catch {
        // Backend not running — that's fine, just show mock events
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleInspect = (event: CanonicalSocialEvent) => {
    setSelectedEvent(event);
    setIsDrawerOpen(true);
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const result = await getAllEvents(200);
      setTelegramEvents(result.items || []);
    } catch { /* ignore */ }
    setIsLoading(false);
  };

  // Filter mock events by search
  const filteredMockEvents = MOCK_EVENTS.filter(
    e =>
      e.content.text.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.author.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.event_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Filter real Telegram events by search
  const filteredTelegramEvents = telegramEvents.filter(
    e =>
      (e.content_text || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (e.author_username || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (e.channel_title || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.event_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalItems = MOCK_EVENTS.length + telegramEvents.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-[#171717]">
            Evidence Vault & Canonical Record Inspector
          </h1>
          <p className="text-xs text-[#6E6A62]">
            SIH Requirement G • Audit trail, raw event provenance, and model grounding pointers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="clay-button-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <span className="badge-mono bg-[#EAE6DD] text-[#3157D5] px-3 py-1 text-xs">
            {totalItems.toLocaleString()} Verified Items Indexed
          </span>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <ClayCard className="p-4 bg-[#FDF9F0] flex items-center justify-between gap-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#6E6A62]" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Search event ID, text keywords, author username, channel..."
            className="w-full bg-[#EAE6DD] text-xs font-sans pl-9 pr-4 py-2 rounded-md border border-[#D8D3C8] focus:border-[#3157D5] focus:outline-none"
          />
        </div>
        <button className="clay-button-secondary text-xs px-3.5 py-2 flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5" /> Filter by Platform
        </button>
      </ClayCard>

      {/* Real Telegram Collected Events */}
      {filteredTelegramEvents.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 mb-3">
            <PlatformBadge platform="telegram" size="md" />
            <h2 className="font-heading font-bold text-base text-[#171717]">
              Telegram — Collected Events
            </h2>
            <span className="text-xs font-mono text-[#6E6A62]">
              ({filteredTelegramEvents.length} items)
            </span>
          </div>

          <div className="space-y-3">
            {filteredTelegramEvents.map(event => (
              <ClayCard key={event.event_id} className="p-5 bg-[#FDF9F0] border-2 border-[#D8D3C8]">
                <div className="flex items-center justify-between mb-3 border-b border-[#D8D3C8] pb-2">
                  <div className="flex items-center gap-2">
                    <PlatformBadge platform="telegram" />
                    <span className="font-mono text-xs text-[#6E6A62]">ID: {event.event_id}</span>
                  </div>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                    event.relevance_score >= 0.8
                      ? 'bg-[#4C8768]/15 text-[#4C8768]'
                      : event.relevance_score >= 0.6
                      ? 'bg-[#3157D5]/15 text-[#3157D5]'
                      : 'bg-[#C18A34]/15 text-[#C18A34]'
                  }`}>
                    Relevance: {Math.round(event.relevance_score * 100)}%
                  </span>
                </div>

                <p className="text-sm font-medium text-[#171717] mb-3 leading-relaxed font-sans">
                  "{event.content_text}"
                </p>

                {/* Posted By & Posted On — prominent info block */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3 p-3 bg-[#EAE6DD] rounded-lg text-xs font-mono">
                  <div>
                    <span className="text-[10px] font-bold text-[#6E6A62] uppercase tracking-wider block mb-0.5">
                      Posted By
                    </span>
                    <span className="text-[#171717] font-semibold">
                      {event.author_display_name || event.author_username || 'Channel Post'}
                    </span>
                    {event.author_username && (
                      <span className="text-[#3157D5] ml-1">@{event.author_username}</span>
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-[#6E6A62] uppercase tracking-wider block mb-0.5">
                      Posted On
                    </span>
                    <span className="text-[#171717] font-semibold">
                      {event.timestamp
                        ? new Date(event.timestamp).toLocaleDateString('en-IN', {
                            weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
                          })
                        : 'Unknown'}
                    </span>
                    {event.timestamp && (
                      <span className="text-[#6E6A62] ml-2">
                        {new Date(event.timestamp).toLocaleTimeString('en-IN', {
                          hour: '2-digit', minute: '2-digit', hour12: true
                        })}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-[#6E6A62] uppercase tracking-wider block mb-0.5">
                      Channel
                    </span>
                    <span className="text-[#171717] font-semibold">
                      {event.channel_title || event.channel_username || 'Unknown'}
                    </span>
                    {event.channel_username && (
                      <span className="text-[#3157D5] ml-1">@{event.channel_username}</span>
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-[#6E6A62] uppercase tracking-wider block mb-0.5">
                      Message ID
                    </span>
                    <span className="text-[#171717] font-semibold">
                      {event.message_id || 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Engagement metrics */}
                <div className="flex items-center gap-4 text-[11px] font-mono text-[#6E6A62] mb-2">
                  <span className="flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5" /> {(event.views || 0).toLocaleString()} views
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare className="w-3.5 h-3.5" /> {(event.replies || 0).toLocaleString()} replies
                  </span>
                  <span className="flex items-center gap-1">
                    <Forward className="w-3.5 h-3.5" /> {(event.forwards || 0).toLocaleString()} forwards
                  </span>
                </div>

                {/* Matched keywords/hashtags */}
                {(event.matched_keywords.length > 0 || event.matched_hashtags.length > 0) && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {event.matched_keywords.map((kw, i) => (
                      <span key={`kw-${i}`} className="text-[10px] font-mono px-1.5 py-0.5 bg-[#3157D5]/10 text-[#3157D5] rounded">
                        {kw}
                      </span>
                    ))}
                    {event.matched_hashtags.map((tag, i) => (
                      <span key={`tag-${i}`} className="text-[10px] font-mono px-1.5 py-0.5 bg-[#4C8768]/10 text-[#4C8768] rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center justify-end text-xs pt-2 border-t border-[#D8D3C8]/60">
                  <a
                    href={event.channel_username ? `https://t.me/${event.channel_username}/${event.message_id}` : '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="clay-button-secondary text-xs py-1 px-3 flex items-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-[#3157D5]" /> View on Telegram
                  </a>
                </div>
              </ClayCard>
            ))}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-8 text-xs font-mono text-[#6E6A62]">
          <RefreshCw className="w-4 h-4 animate-spin text-[#3157D5]" />
          Loading collected events from backend...
        </div>
      )}

      {/* No Telegram results message */}
      {!isLoading && telegramEvents.length === 0 && (
        <ClayCard className="p-5 bg-[#FDF9F0] text-center">
          <p className="text-xs font-mono text-[#6E6A62]">
            No Telegram events collected yet. Go to <strong>Setup Collection</strong> → enter a topic → click <strong>Launch Collection Pipeline</strong> to collect real data.
          </p>
        </ClayCard>
      )}

      {/* Divider between real and mock */}
      {filteredTelegramEvents.length > 0 && filteredMockEvents.length > 0 && (
        <div className="flex items-center gap-3 py-2">
          <div className="flex-1 h-px bg-[#D8D3C8]" />
          <span className="text-[10px] font-mono text-[#6E6A62] uppercase tracking-wider">
            Other Platform Events (Demo Data)
          </span>
          <div className="flex-1 h-px bg-[#D8D3C8]" />
        </div>
      )}

      {/* Original Mock Social Event Records */}
      <div className="space-y-3">
        {filteredMockEvents.map(event => (
          <ClayCard key={event.event_id} className="p-5 bg-[#FDF9F0] border-2 border-[#D8D3C8]">
            <div className="flex items-center justify-between mb-3 border-b border-[#D8D3C8] pb-2">
              <div className="flex items-center gap-2">
                <PlatformBadge platform={event.platform} />
                <span className="font-mono text-xs text-[#6E6A62]">ID: {event.event_id}</span>
              </div>
              <div className="flex items-center gap-2">
                <ConfidenceBadge score={event.analysis.sentiment.score} />
                <span className="font-mono text-xs text-[#6E6A62]">{event.timestamps.created_at}</span>
              </div>
            </div>

            <p className="text-sm font-medium text-[#171717] mb-3 leading-relaxed font-sans">
              "{event.content.text}"
            </p>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-[#D8D3C8]/60">
              <span className="font-mono text-[#6E6A62]">
                Author: <strong className="text-[#171717]">@{event.author.username}</strong> ({event.author.display_name})
              </span>
              <button
                onClick={() => handleInspect(event)}
                className="clay-button-secondary text-xs py-1 px-3 flex items-center gap-1.5"
              >
                <Code2 className="w-3.5 h-3.5 text-[#3157D5]" /> Inspect Provenance & JSON
              </button>
            </div>
          </ClayCard>
        ))}
      </div>

      {/* Evidence Drawer Modal */}
      <EvidenceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        event={selectedEvent}
      />
    </div>
  );
};
