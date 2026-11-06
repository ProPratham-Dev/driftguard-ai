import { useState, useEffect, useRef, useCallback } from 'react';

export function useDriftGuardSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [driftStatus, setDriftStatus] = useState({
    drift_detected: false,
    severity: 'NORMAL',
    drift_score: 0.0,
    current_error_rate: 0.0,
    reference_error_rate: 0.0,
    recent_samples_count: 0,
    status_message: 'Monitoring transaction stream...'
  });
  const [driftEvents, setDriftEvents] = useState([]);
  const [simulatorStatus, setSimulatorStatus] = useState({
    is_running: false,
    is_paused: false,
    fraud_regime: 'normal',
    interval_ms: 500,
    feedback_delay_ms: 3000,
    adaptive_learning_enabled: true,
    transactions_generated: 0,
    feedback_processed: 0,
    fraud_count_simulated: 0,
    fraud_detected_fixed: 0,
    fraud_detected_adaptive: 0,
    fraud_missed_fixed: 0,
    fraud_missed_adaptive: 0,
    active_adaptive_version: 'v1.0-baseline'
  });
  const [modelVersions, setModelVersions] = useState([]);
  const [comparisonMetrics, setComparisonMetrics] = useState(null);

  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Performance Optimization: Batch incoming transactions to avoid re-render churn
  const txBufferRef = useRef([]);
  const flushTimerRef = useRef(null);

  const flushTransactionBuffer = useCallback(() => {
    if (txBufferRef.current.length > 0) {
      const incoming = [...txBufferRef.current];
      txBufferRef.current = [];
      setTransactions((prev) => [...incoming, ...prev].slice(0, 100));
    }
  }, []);

  // Initial REST Sync
  const fetchInitialData = useCallback(async () => {
    try {
      const [simRes, driftRes, versionsRes, compRes, eventsRes] = await Promise.all([
        fetch('/api/simulator/status').then((r) => (r.ok ? r.json() : null)),
        fetch('/api/drift/status').then((r) => (r.ok ? r.json() : null)),
        fetch('/api/models/versions').then((r) => (r.ok ? r.json() : [])),
        fetch('/api/metrics/comparison?window=200').then((r) => (r.ok ? r.json() : null)),
        fetch('/api/drift/events?limit=20').then((r) => (r.ok ? r.json() : []))
      ]);

      if (simRes) setSimulatorStatus(simRes);
      if (driftRes) setDriftStatus(driftRes);
      if (versionsRes) setModelVersions(versionsRes);
      if (compRes) setComparisonMetrics(compRes);
      if (eventsRes) setDriftEvents(eventsRes);
    } catch (err) {
      console.warn('Initial REST sync error:', err);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();

    // Flush batch buffer every 120ms for smooth 60fps UI
    flushTimerRef.current = setInterval(flushTransactionBuffer, 120);

    let isMounted = true;

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live`;

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) return;
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const payload = JSON.parse(event.data);
          const { event: eventType, data } = payload;

          if (eventType === 'connection_established') {
            if (data.simulator) setSimulatorStatus(data.simulator);
            if (data.drift) setDriftStatus(data.drift);
          } else if (eventType === 'new_transaction') {
            // Buffer new transaction
            txBufferRef.current.unshift(data);
            setSimulatorStatus((prev) => ({
              ...prev,
              transactions_generated: prev.transactions_generated + 1
            }));
          } else if (eventType === 'verified_feedback') {
            // Update matching transaction in table
            setTransactions((prev) =>
              prev.map((tx) =>
                tx.tx_id === data.tx_id
                  ? {
                      ...tx,
                      feedback_status: 'verified',
                      ground_truth: data.ground_truth,
                      prediction_correct: data.prediction_correct
                    }
                  : tx
              )
            );
            if (data.drift_status) {
              setDriftStatus(data.drift_status);
            }
            setSimulatorStatus((prev) => ({
              ...prev,
              feedback_processed: prev.feedback_processed + 1
            }));
          } else if (eventType === 'drift_alert') {
            setDriftStatus(data);
            setDriftEvents((prev) => [
              {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                detector_name: 'ASW-DD',
                severity: data.severity,
                details: data.status_message,
                delta_or_stat: data.drift_score,
                pre_drift_mean: data.reference_error_rate,
                post_drift_mean: data.current_error_rate
              },
              ...prev.slice(0, 24)
            ]);
          } else if (eventType === 'model_update') {
            fetch('/api/models/versions').then((r) => r.ok && r.json()).then((v) => v && setModelVersions(v));
            fetch('/api/metrics/comparison?window=200').then((r) => r.ok && r.json()).then((c) => c && setComparisonMetrics(c));
          } else if (eventType === 'simulator_status') {
            setSimulatorStatus(data);
          }
        } catch (err) {
          console.error('WebSocket payload parsing error:', err);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        ws.close();
      };
    }

    connect();

    // Periodic metrics comparison refresh
    const metricsInterval = setInterval(() => {
      fetch('/api/metrics/comparison?window=200')
        .then((r) => (r.ok ? r.json() : null))
        .then((comp) => comp && setComparisonMetrics(comp))
        .catch(() => {});
    }, 3500);

    return () => {
      isMounted = false;
      clearInterval(metricsInterval);
      if (flushTimerRef.current) clearInterval(flushTimerRef.current);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [fetchInitialData, flushTransactionBuffer]);

  // Actions
  const startSimulator = useCallback(async () => {
    const res = await fetch('/api/simulator/start', { method: 'POST' });
    if (res.ok) setSimulatorStatus(await res.json());
  }, []);

  const pauseSimulator = useCallback(async () => {
    const res = await fetch('/api/simulator/pause', { method: 'POST' });
    if (res.ok) setSimulatorStatus(await res.json());
  }, []);

  const resumeSimulator = useCallback(async () => {
    const res = await fetch('/api/simulator/resume', { method: 'POST' });
    if (res.ok) setSimulatorStatus(await res.json());
  }, []);

  const stopSimulator = useCallback(async () => {
    const res = await fetch('/api/simulator/stop', { method: 'POST' });
    if (res.ok) setSimulatorStatus(await res.json());
  }, []);

  const updateConfig = useCallback(async (newConfig) => {
    const res = await fetch('/api/simulator/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newConfig)
    });
    if (res.ok) setSimulatorStatus(await res.json());
  }, []);

  const triggerRollback = useCallback(async () => {
    const res = await fetch('/api/learning/rollback', { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      fetch('/api/models/versions').then((r) => r.ok && r.json()).then((v) => v && setModelVersions(v));
      return data;
    }
    return { success: false, message: 'Rollback failed.' };
  }, []);

  return {
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
  };
}
