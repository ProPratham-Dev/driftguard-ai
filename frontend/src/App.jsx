import React from 'react';
import Header from './components/Header';
import KpiCards from './components/KpiCards';
import SimulatorControls from './components/SimulatorControls';
import ModelComparison from './components/ModelComparison';
import DriftMonitor from './components/DriftMonitor';
import LiveTransactionFeed from './components/LiveTransactionFeed';
import ModelLifecycle from './components/ModelLifecycle';
import { useDriftGuardSocket } from './hooks/useDriftGuardSocket';

export default function App() {
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
    <div className="min-h-screen bg-[#060b17] text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      
      {/* Top Header */}
      <Header
        isConnected={isConnected}
        simulatorStatus={simulatorStatus}
      />

      {/* Main Dashboard Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        
        {/* Section 1: KPI Overview Cards */}
        <KpiCards
          simulatorStatus={simulatorStatus}
          driftStatus={driftStatus}
        />

        {/* Section 2: Interactive Simulation Controls */}
        <SimulatorControls
          simulatorStatus={simulatorStatus}
          startSimulator={startSimulator}
          pauseSimulator={pauseSimulator}
          resumeSimulator={resumeSimulator}
          stopSimulator={stopSimulator}
          updateConfig={updateConfig}
        />

        {/* Section 3: Dual Grid (Model Comparison + Drift Monitor) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ModelComparison
            comparisonMetrics={comparisonMetrics}
          />
          <DriftMonitor
            driftStatus={driftStatus}
            driftEvents={driftEvents}
          />
        </div>

        {/* Section 4: Live Transaction Stream Table */}
        <LiveTransactionFeed
          transactions={transactions}
        />

        {/* Section 5: Model Governance & Version Rollback */}
        <ModelLifecycle
          modelVersions={modelVersions}
          triggerRollback={triggerRollback}
        />

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-[#040812] py-4 px-6 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>DRIFTGUARD AI — Real-Time Adaptive Fraud Detection Platform</span>
          <span>NeuroForge 2026: The Moving Target</span>
        </div>
      </footer>

    </div>
  );
}
