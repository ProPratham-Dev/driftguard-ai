import React, { useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import KpiCards from './components/KpiCards';
import SimulatorControls from './components/SimulatorControls';
import ModelComparison from './components/ModelComparison';
import DriftMonitor from './components/DriftMonitor';
import LiveTransactionFeed from './components/LiveTransactionFeed';
import ModelLifecycle from './components/ModelLifecycle';
import { useDriftGuardSocket } from './hooks/useDriftGuardSocket';
import { ThemeProvider } from './context/ThemeContext';

function DashboardContent() {
  const [activeSection, setActiveSection] = useState('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const {
    isConnected,
    transactions,
    driftStatus,
    driftEvents,
    simulatorStatus,
    modelVersions,
    comparisonMetrics,
    startSimulator,
    pauseSimulator,
    resumeSimulator,
    stopSimulator,
    updateConfig,
    triggerRollback
  } = useDriftGuardSocket();

  return (
    <div className="min-h-screen bg-app flex text-primary">
      {/* Sidebar Navigation */}
      <Sidebar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          isConnected={isConnected}
          simulatorStatus={simulatorStatus}
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
        />

        <main className="flex-1 p-4 sm:p-6 max-w-7xl w-full mx-auto space-y-5">
          {/* Section 1: KPI Cards */}
          <KpiCards
            simulatorStatus={simulatorStatus}
            driftStatus={driftStatus}
          />

          {/* Section 2: Simulator Controls */}
          <SimulatorControls
            simulatorStatus={simulatorStatus}
            startSimulator={startSimulator}
            pauseSimulator={pauseSimulator}
            resumeSimulator={resumeSimulator}
            stopSimulator={stopSimulator}
            updateConfig={updateConfig}
          />

          {/* Section 3: Dual Grid (Model Comparison + Drift Monitoring) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <ModelComparison
              comparisonMetrics={comparisonMetrics}
            />
            <DriftMonitor
              driftStatus={driftStatus}
              driftEvents={driftEvents}
            />
          </div>

          {/* Section 4: Live Transaction Table */}
          <LiveTransactionFeed
            transactions={transactions}
          />

          {/* Section 5: Model Governance & Rollback */}
          <ModelLifecycle
            modelVersions={modelVersions}
            triggerRollback={triggerRollback}
          />
        </main>

        {/* Footer */}
        <footer className="border-t border-theme bg-card py-4 px-6 text-xs text-secondary font-mono">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
            <span>DRIFTGUARD AI — Adaptive Real-Time Fraud & Concept Drift Defense System</span>
            <span>NeuroForge 2026: The Moving Target</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <DashboardContent />
    </ThemeProvider>
  );
}
