import React, { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { CollectionSetupPage } from './pages/CollectionSetupPage';
import { CollectionStatusPage } from './pages/CollectionStatusPage';
import { SentimentPage } from './pages/SentimentPage';
import { AudiencePage } from './pages/AudiencePage';
import { TopicExplorerPage } from './pages/TopicExplorerPage';
import { TrendsPage } from './pages/TrendsPage';
import { NetworkPage } from './pages/NetworkPage';
import { CrossPlatformPage } from './pages/CrossPlatformPage';
import { EvidenceVaultPage } from './pages/EvidenceVaultPage';
import { AIAnalystPage } from './pages/AIAnalystPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('landing');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  // If on public portal / landing page, render standalone view
  if (activeTab === 'landing') {
    return (
      <LandingPage
        onStartAnalysis={() => setActiveTab('collect')}
        onExploreDashboard={() => setActiveTab('dashboard')}
      />
    );
  }

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardPage onNavigate={(tab) => setActiveTab(tab)} />;
      case 'collect':
        return (
          <CollectionSetupPage
            onStartCollection={(jobId?: string) => {
              if (jobId) setCurrentJobId(jobId);
              setActiveTab('status');
            }}
          />
        );
      case 'status':
        return (
          <CollectionStatusPage
            jobId={currentJobId}
            onProceedToDashboard={() => setActiveTab('dashboard')}
          />
        );
      case 'sentiment':
        return <SentimentPage />;
      case 'audience':
        return <AudiencePage />;
      case 'topics':
        return <TopicExplorerPage />;
      case 'trends':
        return <TrendsPage />;
      case 'network':
        return <NetworkPage />;
      case 'platforms':
        return <CrossPlatformPage />;
      case 'evidence':
        return <EvidenceVaultPage />;
      case 'ai-analyst':
        return <AIAnalystPage />;
      case 'reports':
        return <ReportsPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <DashboardPage onNavigate={(tab) => setActiveTab(tab)} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-[#F5F3EE] text-[#171717] font-sans antialiased">
      {/* Global Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          activeTab={activeTab}
          onOpenCollect={() => setActiveTab('collect')}
          onOpenReport={() => setActiveTab('reports')}
        />
        <main className="flex-1 p-8 overflow-y-auto">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
}

export default App;
