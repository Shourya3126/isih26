import React, { useState, useEffect } from 'react';
import { ClayCard } from '../components/ui/ClayCard';
import { PlatformBadge } from '../components/ui/PlatformBadge';
import { Database, Play, CheckCircle2, Sliders, Info, Clock, Layers, Loader2, AlertCircle } from 'lucide-react';
import { INITIAL_PLATFORMS } from '../services/mockData';
import { startTelegramCollection, getTelegramConnectionStatus } from '../services/api';
import type { PlatformConfig } from '../types';

interface CollectionSetupPageProps {
  onStartCollection: (jobId?: string) => void;
}

/** Map time-window select values to hours */
const TIME_WINDOW_HOURS: Record<string, number> = {
  '1h': 1,
  '6h': 6,
  '24h': 24,
  '7d': 168,
  '30d': 720,
};

export const CollectionSetupPage: React.FC<CollectionSetupPageProps> = ({ onStartCollection }) => {
  const [platforms, setPlatforms] = useState<PlatformConfig[]>(INITIAL_PLATFORMS);
  const [topicQuery, setTopicQuery] = useState('AI Regulation & Social Intelligence');
  const [hashtags, setHashtags] = useState('#AIRegulation, #AgenticAI, #DataPrivacy');
  const [mentions, setMentions] = useState('@tech_analyst_raj, @ai_policy_lab');
  const [timeWindow, setTimeWindow] = useState('24h');
  const [recentPct, setRecentPct] = useState(60);
  const [engagementPct, setEngagementPct] = useState(20);
  const [velocityPct, setVelocityPct] = useState(20);

  // Real Telegram connection state
  const [isLaunching, setIsLaunching] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);

  // Fetch real Telegram connection status on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await getTelegramConnectionStatus();
        if (cancelled) return;
        setPlatforms(prev =>
          prev.map(p =>
            p.id === 'telegram'
              ? {
                  ...p,
                  status: result.connected ? 'connected' : 'partially_configured',
                }
              : p
          )
        );
      } catch {
        // Backend not reachable — mark Telegram as partially_configured
        if (cancelled) return;
        setPlatforms(prev =>
          prev.map(p =>
            p.id === 'telegram'
              ? { ...p, status: 'partially_configured' as const }
              : p
          )
        );
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleTargetChange = (id: string, newTarget: number) => {
    setPlatforms(prev =>
      prev.map(p => (p.id === id ? { ...p, targetItems: newTarget } : p))
    );
  };

  const handleTogglePlatform = (id: string) => {
    setPlatforms(prev =>
      prev.map(p =>
        p.id === id
          ? {
              ...p,
              status: p.status === 'disabled' ? 'connected' : 'disabled'
            }
          : p
      )
    );
  };

  /** Parse comma-separated input into a trimmed array */
  const parseList = (raw: string): string[] =>
    raw.split(',').map(s => s.trim()).filter(Boolean);

  /** Extract keywords from topic string */
  const topicToKeywords = (topic: string): string[] =>
    topic
      .split(/[\s&,]+/)
      .map(w => w.trim().toLowerCase())
      .filter(w => w.length > 2);

  const handleLaunchCollection = async () => {
    setIsLaunching(true);
    setLaunchError(null);

    const telegramPlatform = platforms.find(p => p.id === 'telegram');
    const telegramEnabled = telegramPlatform && telegramPlatform.status !== 'disabled';

    if (!telegramEnabled) {
      // Fall back to original dummy behavior for other platforms
      setIsLaunching(false);
      onStartCollection();
      return;
    }

    try {
      const result = await startTelegramCollection({
        topic: topicQuery,
        keywords: topicToKeywords(topicQuery),
        hashtags: parseList(hashtags),
        handles: parseList(mentions),
        lookback_hours: TIME_WINDOW_HOURS[timeWindow] ?? 24,
        target_items: telegramPlatform.targetItems,
      });

      setIsLaunching(false);
      onStartCollection(result.job_id);
    } catch (err: any) {
      setIsLaunching(false);
      setLaunchError(err.message || 'Failed to start collection');
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-[#171717]">
            Data Collection & Ingestion Setup
          </h1>
          <p className="text-xs text-[#6E6A62]">
            SIH Requirement A • Multi-platform continuous data collection & timeline target configuration
          </p>
        </div>

        <button
          onClick={handleLaunchCollection}
          disabled={isLaunching}
          className={`clay-button text-sm px-5 py-2.5 flex items-center gap-2 ${
            isLaunching ? 'opacity-70 cursor-not-allowed' : ''
          }`}
        >
          {isLaunching ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Collection Running...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Launch Collection Pipeline</span>
            </>
          )}
        </button>
      </div>

      {/* Launch Error Banner */}
      {launchError && (
        <div className="bg-[#C15D5D]/10 border border-[#C15D5D]/30 p-4 rounded-lg flex items-start gap-3 text-xs text-[#171717]">
          <AlertCircle className="w-4 h-4 text-[#C15D5D] shrink-0 mt-0.5" />
          <div>
            <span className="font-mono font-bold text-[#C15D5D] uppercase tracking-wide block mb-0.5">
              Collection Error
            </span>
            <p className="text-[#171717]/90 leading-relaxed">{launchError}</p>
          </div>
        </div>
      )}

      {/* Target Item Count Notice (SIH Spec Rule) */}
      <div className="bg-[#3157D5]/10 border border-[#3157D5]/30 p-4 rounded-lg flex items-start gap-3 text-xs text-[#171717]">
        <Info className="w-4 h-4 text-[#3157D5] shrink-0 mt-0.5" />
        <div>
          <span className="font-mono font-bold text-[#3157D5] uppercase tracking-wide block mb-0.5">
            Item-Count Target Architecture
          </span>
          <p className="text-[#171717]/90 leading-relaxed">
            Collection targets refer strictly to <strong>valid unique deduplicated items</strong> collected, not elapsed time. The system will continue incremental fetching until the item-count cap is met or stream expires.
          </p>
        </div>
      </div>

      {/* Query & Topic Configuration */}
      <ClayCard className="p-6 bg-[#FDF9F0]">
        <div className="flex items-center gap-2 mb-4 border-b border-[#D8D3C8] pb-3">
          <Sliders className="w-5 h-5 text-[#3157D5]" />
          <h2 className="font-heading font-bold text-base text-[#171717]">
            Primary Ingestion Query Parameters
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="font-mono font-semibold uppercase text-[#6E6A62] block mb-1">
              Topic / Keywords
            </label>
            <input
              type="text"
              value={topicQuery}
              onChange={e => setTopicQuery(e.target.value)}
              className="w-full bg-[#EAE6DD] text-[#171717] font-sans p-2.5 rounded-md border border-[#D8D3C8] focus:border-[#3157D5] focus:outline-none"
            />
          </div>

          <div>
            <label className="font-mono font-semibold uppercase text-[#6E6A62] block mb-1">
              Target Hashtags (Comma separated)
            </label>
            <input
              type="text"
              value={hashtags}
              onChange={e => setHashtags(e.target.value)}
              className="w-full bg-[#EAE6DD] text-[#171717] font-sans p-2.5 rounded-md border border-[#D8D3C8] focus:border-[#3157D5] focus:outline-none"
            />
          </div>

          <div>
            <label className="font-mono font-semibold uppercase text-[#6E6A62] block mb-1">
              Account Mentions / Handles
            </label>
            <input
              type="text"
              value={mentions}
              onChange={e => setMentions(e.target.value)}
              className="w-full bg-[#EAE6DD] text-[#171717] font-sans p-2.5 rounded-md border border-[#D8D3C8] focus:border-[#3157D5] focus:outline-none"
            />
          </div>

          <div>
            <label className="font-mono font-semibold uppercase text-[#6E6A62] block mb-1">
              Historical Lookback Time Window
            </label>
            <select
              value={timeWindow}
              onChange={e => setTimeWindow(e.target.value)}
              className="w-full bg-[#EAE6DD] text-[#171717] font-sans p-2.5 rounded-md border border-[#D8D3C8] focus:border-[#3157D5] focus:outline-none"
            >
              <option value="1h">Last 1 Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
          </div>
        </div>
      </ClayCard>

      {/* Multi-Platform Connector Selection & Item Caps */}
      <ClayCard className="p-6 bg-[#FDF9F0]">
        <div className="flex items-center justify-between mb-4 border-b border-[#D8D3C8] pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-[#DE775A]" />
            <h2 className="font-heading font-bold text-base text-[#171717]">
              Platform Selection & Target Item-Counts
            </h2>
          </div>
          <span className="text-xs font-mono text-[#6E6A62]">6 Connectors Available</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {platforms.map(platform => (
            <div
              key={platform.id}
              className={`p-4 rounded-lg border transition-all ${
                platform.status !== 'disabled'
                  ? 'bg-[#EAE6DD] border-[#D8D3C8]'
                  : 'bg-[#EAE6DD]/50 border-[#D8D3C8]/50 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={platform.status !== 'disabled'}
                    onChange={() => handleTogglePlatform(platform.id)}
                    className="w-4 h-4 rounded text-[#3157D5] focus:ring-0"
                  />
                  <PlatformBadge platform={platform.id} size="md" />
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    platform.status === 'connected'
                      ? 'bg-[#4C8768]/15 text-[#4C8768]'
                      : platform.status === 'partially_configured'
                      ? 'bg-[#C18A34]/15 text-[#C18A34]'
                      : 'bg-[#6E6A62]/15 text-[#6E6A62]'
                  }`}
                >
                  {platform.status.replace('_', ' ')}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-[#6E6A62]">Target Items Cap:</span>
                <input
                  type="number"
                  value={platform.targetItems}
                  onChange={e => handleTargetChange(platform.id, parseInt(e.target.value) || 0)}
                  disabled={platform.status === 'disabled'}
                  className="w-24 bg-[#FDF9F0] font-mono text-right p-1 rounded border border-[#D8D3C8] focus:border-[#3157D5] focus:outline-none"
                />
              </div>
            </div>
          ))}
        </div>
      </ClayCard>

      {/* Sampling Strategy Heuristics */}
      <ClayCard className="p-6 bg-[#FDF9F0]">
        <div className="flex items-center gap-2 mb-4 border-b border-[#D8D3C8] pb-3">
          <Layers className="w-5 h-5 text-[#4C8768]" />
          <h2 className="font-heading font-bold text-base text-[#171717]">
            Heuristic Sampling Strategy Weights
          </h2>
        </div>

        <div className="grid grid-cols-3 gap-6 text-center text-xs">
          <div className="p-3 bg-[#EAE6DD] rounded-lg">
            <span className="font-mono text-lg font-bold text-[#3157D5] block">{recentPct}%</span>
            <span className="font-semibold text-[#171717] block mt-1">Recent & Relevant</span>
            <span className="text-[10px] text-[#6E6A62]">Chronological baseline</span>
          </div>

          <div className="p-3 bg-[#EAE6DD] rounded-lg">
            <span className="font-mono text-lg font-bold text-[#DE775A] block">{engagementPct}%</span>
            <span className="font-semibold text-[#171717] block mt-1">High Engagement</span>
            <span className="text-[10px] text-[#6E6A62]">Amplified posts</span>
          </div>

          <div className="p-3 bg-[#EAE6DD] rounded-lg">
            <span className="font-mono text-lg font-bold text-[#4C8768] block">{velocityPct}%</span>
            <span className="font-semibold text-[#171717] block mt-1">High Velocity</span>
            <span className="text-[10px] text-[#6E6A62]">Accelerating signals</span>
          </div>
        </div>
      </ClayCard>
    </div>
  );
};
