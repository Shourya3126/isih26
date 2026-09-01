import React, { useState, useEffect, useRef } from 'react';
import { ClayCard } from '../components/ui/ClayCard';
import { PlatformBadge } from '../components/ui/PlatformBadge';
import { INITIAL_PLATFORMS, MOCK_PIPELINE_STEPS } from '../services/mockData';
import { getJobStatus, getJobResults } from '../services/api';
import type { JobStatusResponse, SocialEventItem } from '../services/api';
import { Activity, CheckCircle2, AlertCircle, RefreshCw, Layers, Database, ArrowRight, XCircle, Eye, Forward, MessageSquare } from 'lucide-react';

interface CollectionStatusPageProps {
  jobId: string | null;
  onProceedToDashboard: () => void;
}

/** Derive pipeline stages from the current job status */
function deriveTelegramPipelineSteps(job: JobStatusResponse | null) {
  if (!job) return [];

  const s = job.status;
  const progress = job.progress;

  const stages = [
    {
      id: 'tg-1',
      name: 'Telegram Connection',
      status: s === 'queued' ? 'in_progress' as const : 'completed' as const,
      progressPct: s === 'queued' ? 50 : 100,
      detailMessage: s === 'queued' ? 'Authenticating with Telegram...' : 'Session authenticated',
    },
    {
      id: 'tg-2',
      name: 'Reading Channel Messages',
      status:
        s === 'queued' ? 'pending' as const :
        s === 'running' && progress < 80 ? 'in_progress' as const :
        'completed' as const,
      progressPct:
        s === 'queued' ? 0 :
        s === 'running' ? Math.min(progress, 95) : 100,
      detailMessage:
        s === 'running' && job.current_channel
          ? `Scanning @${job.current_channel} (${job.channels_checked}/${job.channels_total} channels) — ${job.messages_scanned.toLocaleString()} messages`
          : s !== 'queued' ? `${job.messages_scanned.toLocaleString()} messages scanned across ${job.channels_checked} channels` : 'Waiting...',
    },
    {
      id: 'tg-3',
      name: 'Relevance Filtering',
      status:
        s === 'running' && progress >= 30 ? 'in_progress' as const :
        (s === 'completed' || s === 'partial') ? 'completed' as const :
        'pending' as const,
      progressPct: (s === 'completed' || s === 'partial') ? 100 : s === 'running' ? Math.min(progress, 90) : 0,
      detailMessage: job.relevant_items > 0
        ? `${job.relevant_items.toLocaleString()} relevant posts found`
        : 'Applying keyword, hashtag, and topic filters',
    },
    {
      id: 'tg-4',
      name: 'Deduplication',
      status:
        (s === 'completed' || s === 'partial') ? 'completed' as const :
        s === 'running' && progress >= 50 ? 'in_progress' as const :
        'pending' as const,
      progressPct: (s === 'completed' || s === 'partial') ? 100 : s === 'running' ? Math.min(progress, 85) : 0,
      detailMessage: job.duplicates_removed > 0
        ? `${job.duplicates_removed} duplicate(s) removed`
        : 'Primary + text-hash deduplication',
    },
    {
      id: 'tg-5',
      name: 'Normalization & Storage',
      status:
        (s === 'completed' || s === 'partial') ? 'completed' as const :
        s === 'running' && progress >= 70 ? 'in_progress' as const :
        'pending' as const,
      progressPct: (s === 'completed' || s === 'partial') ? 100 : s === 'running' ? Math.min(progress, 80) : 0,
      detailMessage: job.final_items > 0
        ? `${job.final_items.toLocaleString()} canonical SocialEvents stored`
        : 'Converting to canonical format',
    },
  ];

  // Mark failed
  if (s === 'failed') {
    const firstPending = stages.find(st => st.status === 'pending' || st.status === 'in_progress');
    if (firstPending) {
      firstPending.status = 'failed' as any;
      firstPending.detailMessage = job.error_message || 'Collection failed';
    }
  }

  return stages;
}

export const CollectionStatusPage: React.FC<CollectionStatusPageProps> = ({ jobId, onProceedToDashboard }) => {
  const [pipelineSteps, setPipelineSteps] = useState(MOCK_PIPELINE_STEPS);
  const [isSimulating, setIsSimulating] = useState(true);

  // Real Telegram job state
  const [telegramJob, setTelegramJob] = useState<JobStatusResponse | null>(null);
  const [telegramResults, setTelegramResults] = useState<SocialEventItem[]>([]);
  const [showResults, setShowResults] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll real job status if we have a jobId
  useEffect(() => {
    if (!jobId) {
      // No real job — just show mock pipeline
      const timer = setTimeout(() => setIsSimulating(false), 2000);
      return () => clearTimeout(timer);
    }

    setIsSimulating(true);

    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        setTelegramJob(status);

        if (status.status === 'completed' || status.status === 'partial' || status.status === 'failed') {
          // Stop polling
          if (pollingRef.current) clearInterval(pollingRef.current);
          setIsSimulating(false);

          // Fetch results for completed/partial jobs
          if (status.status !== 'failed' && status.final_items > 0) {
            try {
              const results = await getJobResults(jobId);
              setTelegramResults(results.items);
            } catch { /* ignore */ }
          }
        }
      } catch {
        // Backend unreachable — stop polling
        if (pollingRef.current) clearInterval(pollingRef.current);
        setIsSimulating(false);
      }
    };

    // Initial fetch
    poll();
    // Poll every 2 seconds
    pollingRef.current = setInterval(poll, 2000);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [jobId]);

  const telegramStages = deriveTelegramPipelineSteps(telegramJob);

  // Build the Telegram platform card data from real job
  const telegramPlatformCard = telegramJob
    ? {
        ...INITIAL_PLATFORMS.find(p => p.id === 'telegram')!,
        targetItems: telegramJob.target_items,
        validUniqueCount: telegramJob.final_items,
        duplicateCount: telegramJob.duplicates_removed,
        errorCount: telegramJob.channel_errors.length,
        completionPercentage: telegramJob.progress,
        status: telegramJob.status === 'failed' ? 'partially_configured' as const : 'connected' as const,
      }
    : null;

  // Use real data for Telegram, mock for others
  const displayPlatforms = INITIAL_PLATFORMS.map(p =>
    p.id === 'telegram' && telegramPlatformCard ? telegramPlatformCard : p
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-[#171717]">
            Live Collection Telemetry & Pipeline Status
          </h1>
          <p className="text-xs text-[#6E6A62]">
            SIH Requirement A • WebSocket/SSE live job progression and per-source telemetry
          </p>
        </div>

        <button
          onClick={onProceedToDashboard}
          className="clay-button text-xs px-4 py-2 flex items-center gap-1.5"
        >
          <span>Explore Computed Analytics</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Per-Platform Ingestion Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {displayPlatforms.map(platform => (
          <ClayCard key={platform.id} className="p-5 bg-[#FDF9F0]">
            <div className="flex items-center justify-between mb-3 border-b border-[#D8D3C8] pb-2">
              <PlatformBadge platform={platform.id} size="md" />
              <span
                className={`font-mono text-xs font-bold ${
                  platform.completionPercentage === 100
                    ? 'text-[#4C8768]'
                    : platform.id === 'telegram' && telegramJob?.status === 'failed'
                    ? 'text-[#C15D5D]'
                    : 'text-[#3157D5]'
                }`}
              >
                {platform.completionPercentage === 100
                  ? 'COMPLETE'
                  : platform.id === 'telegram' && telegramJob?.status === 'failed'
                  ? 'FAILED'
                  : platform.id === 'telegram' && telegramJob?.status === 'running'
                  ? 'COLLECTING'
                  : 'INGESTING'}
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono mb-4">
              <div className="flex justify-between">
                <span className="text-[#6E6A62]">Target Items Cap:</span>
                <span className="text-[#171717] font-semibold">{platform.targetItems.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6E6A62]">Valid Unique Fetched:</span>
                <span className="text-[#4C8768] font-bold">{platform.validUniqueCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6E6A62]">Deduplicated Items:</span>
                <span className="text-[#DE775A]">{platform.duplicateCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6E6A62]">API Errors / Skipped:</span>
                <span className="text-[#C15D5D]">{platform.errorCount}</span>
              </div>
              {/* Show current channel for Telegram while running */}
              {platform.id === 'telegram' && telegramJob?.status === 'running' && telegramJob.current_channel && (
                <div className="flex justify-between">
                  <span className="text-[#6E6A62]">Current Channel:</span>
                  <span className="text-[#3157D5] font-semibold">@{telegramJob.current_channel}</span>
                </div>
              )}
              {/* Messages scanned for Telegram */}
              {platform.id === 'telegram' && telegramJob && telegramJob.messages_scanned > 0 && (
                <div className="flex justify-between">
                  <span className="text-[#6E6A62]">Messages Scanned:</span>
                  <span className="text-[#171717] font-semibold">{telegramJob.messages_scanned.toLocaleString()}</span>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-[#6E6A62]">Progress</span>
                <span className="font-bold text-[#171717]">{platform.completionPercentage}%</span>
              </div>
              <div className="w-full bg-[#EAE6DD] h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    platform.id === 'telegram' && telegramJob?.status === 'failed'
                      ? 'bg-[#C15D5D]'
                      : 'bg-[#3157D5]'
                  }`}
                  style={{ width: `${platform.completionPercentage}%` }}
                ></div>
              </div>
            </div>
          </ClayCard>
        ))}
      </div>

      {/* Telegram Pipeline Stages (when we have a real job) */}
      {jobId && telegramStages.length > 0 && (
        <ClayCard className="p-6 bg-[#FDF9F0]">
          <div className="flex items-center justify-between mb-4 border-b border-[#D8D3C8] pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-[#3157D5]" />
              <h2 className="font-heading font-bold text-base text-[#171717]">
                Telegram Collection Pipeline
              </h2>
            </div>
            {isSimulating ? (
              <span className="flex items-center gap-1.5 text-xs font-mono text-[#3157D5]">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Collection Active
              </span>
            ) : telegramJob?.status === 'failed' ? (
              <span className="flex items-center gap-1.5 text-xs font-mono text-[#C15D5D] font-semibold">
                <XCircle className="w-3.5 h-3.5" /> Failed
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-mono text-[#4C8768] font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Pipeline Complete
              </span>
            )}
          </div>

          <div className="space-y-3">
            {telegramStages.map(step => (
              <div
                key={step.id}
                className="p-3.5 bg-[#EAE6DD] rounded-lg border border-[#D8D3C8] flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  {step.status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-[#4C8768] shrink-0" />
                  ) : step.status === 'failed' ? (
                    <XCircle className="w-5 h-5 text-[#C15D5D] shrink-0" />
                  ) : step.status === 'in_progress' ? (
                    <RefreshCw className="w-5 h-5 text-[#3157D5] animate-spin shrink-0" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-[#D8D3C8] shrink-0" />
                  )}
                  <div>
                    <h3 className="font-heading font-bold text-sm text-[#171717]">{step.name}</h3>
                    {step.detailMessage && (
                      <span className="text-xs text-[#6E6A62] font-mono">{step.detailMessage}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-[#171717]">
                    {step.progressPct}%
                  </span>
                  <span className={`badge-mono border border-[#D8D3C8] ${
                    step.status === 'completed' ? 'bg-[#4C8768]/10 text-[#4C8768]' :
                    step.status === 'failed' ? 'bg-[#C15D5D]/10 text-[#C15D5D]' :
                    'bg-[#FDF9F0] text-[#3157D5]'
                  }`}>
                    {step.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Channel errors */}
          {telegramJob?.channel_errors && telegramJob.channel_errors.length > 0 && (
            <div className="mt-4 p-3 bg-[#C15D5D]/5 border border-[#C15D5D]/20 rounded-lg">
              <h4 className="text-xs font-mono font-bold text-[#C15D5D] mb-2">Channel Errors</h4>
              {telegramJob.channel_errors.map((err, i) => (
                <div key={i} className="text-xs font-mono text-[#6E6A62] mb-1">
                  <span className="text-[#C15D5D]">@{err.channel}</span>: {err.error}
                </div>
              ))}
            </div>
          )}
        </ClayCard>
      )}

      {/* Analysis Pipeline Steps Sequence (original mock for other platforms) */}
      <ClayCard className="p-6 bg-[#FDF9F0]">
        <div className="flex items-center justify-between mb-4 border-b border-[#D8D3C8] pb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#3157D5]" />
            <h2 className="font-heading font-bold text-base text-[#171717]">
              Multi-Stage Analytical Pipeline Progress
            </h2>
          </div>
          {isSimulating ? (
            <span className="flex items-center gap-1.5 text-xs font-mono text-[#3157D5]">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Stream Ingestion Active
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs font-mono text-[#4C8768] font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" /> Pipeline Ready
            </span>
          )}
        </div>

        <div className="space-y-3">
          {pipelineSteps.map(step => (
            <div
              key={step.id}
              className="p-3.5 bg-[#EAE6DD] rounded-lg border border-[#D8D3C8] flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                {step.status === 'completed' ? (
                  <CheckCircle2 className="w-5 h-5 text-[#4C8768] shrink-0" />
                ) : (
                  <RefreshCw className="w-5 h-5 text-[#3157D5] animate-spin shrink-0" />
                )}
                <div>
                  <h3 className="font-heading font-bold text-sm text-[#171717]">{step.name}</h3>
                  {step.detailMessage && (
                    <span className="text-xs text-[#6E6A62] font-mono">{step.detailMessage}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-bold text-[#171717]">
                  {step.progressPct}%
                </span>
                <span className="badge-mono bg-[#FDF9F0] text-[#3157D5] border border-[#D8D3C8]">
                  {step.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </ClayCard>

      {/* Telegram Results Section (appears after collection completes) */}
      {telegramResults.length > 0 && (
        <ClayCard className="p-6 bg-[#FDF9F0]">
          <div className="flex items-center justify-between mb-4 border-b border-[#D8D3C8] pb-3">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-[#24A1DE]" />
              <h2 className="font-heading font-bold text-base text-[#171717]">
                Telegram Collection Results
              </h2>
              <span className="text-xs font-mono text-[#6E6A62]">
                {telegramResults.length} items
              </span>
            </div>
            <button
              onClick={() => setShowResults(!showResults)}
              className="text-xs font-mono font-semibold text-[#3157D5] hover:underline"
            >
              {showResults ? 'Hide Results' : 'Show Results'}
            </button>
          </div>

          {showResults && (
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {telegramResults.map(item => (
                <div
                  key={item.event_id}
                  className="p-4 bg-[#EAE6DD] rounded-lg border border-[#D8D3C8]"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <PlatformBadge platform="telegram" size="sm" />
                      <span className="font-heading font-bold text-sm text-[#171717]">
                        {item.channel_title || item.channel_username || 'Unknown Channel'}
                      </span>
                    </div>
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                      item.relevance_score >= 0.8
                        ? 'bg-[#4C8768]/15 text-[#4C8768]'
                        : item.relevance_score >= 0.6
                        ? 'bg-[#3157D5]/15 text-[#3157D5]'
                        : 'bg-[#C18A34]/15 text-[#C18A34]'
                    }`}>
                      Relevance: {Math.round(item.relevance_score * 100)}%
                    </span>
                  </div>

                  {/* Post text */}
                  <p className="text-xs text-[#171717]/90 leading-relaxed mb-3 line-clamp-4">
                    {item.content_text}
                  </p>

                  {/* Engagement row */}
                  <div className="flex items-center gap-4 text-[11px] font-mono text-[#6E6A62] mb-2">
                    <span className="flex items-center gap-1">
                      <Eye className="w-3.5 h-3.5" /> {(item.views || 0).toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3.5 h-3.5" /> {(item.replies || 0).toLocaleString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <Forward className="w-3.5 h-3.5" /> {(item.forwards || 0).toLocaleString()}
                    </span>
                    {item.timestamp && (
                      <span className="text-[#6E6A62]">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                    )}
                  </div>

                  {/* Matched keywords/hashtags */}
                  {(item.matched_keywords.length > 0 || item.matched_hashtags.length > 0) && (
                    <div className="flex flex-wrap gap-1.5">
                      {item.matched_keywords.map((kw, i) => (
                        <span key={`kw-${i}`} className="text-[10px] font-mono px-1.5 py-0.5 bg-[#3157D5]/10 text-[#3157D5] rounded">
                          {kw}
                        </span>
                      ))}
                      {item.matched_hashtags.map((tag, i) => (
                        <span key={`tag-${i}`} className="text-[10px] font-mono px-1.5 py-0.5 bg-[#4C8768]/10 text-[#4C8768] rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ClayCard>
      )}
    </div>
  );
};
