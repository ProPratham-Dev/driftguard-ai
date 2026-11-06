import asyncio
import time
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from collections import deque

from backend.app.ml.dataset_generator import SyntheticDatasetGenerator
from backend.app.services.adaptive_learning_service import adaptive_service
from backend.app.core.database import SessionLocal
from backend.app.core.websocket_manager import ws_manager
from backend.app.models.db_models import DBTransaction

logger = logging.getLogger("driftguard.simulator")

class TransactionSimulator:
    """
    Asynchronous Real-Time Transaction Simulator.
    Generates time-ordered continuous financial transactions using SyntheticDatasetGenerator,
    records predictions before label revelation, queues realistic delayed feedback,
    and broadcasts events over WebSockets.
    """

    def __init__(self):
        self.generator = SyntheticDatasetGenerator(seed=int(time.time()))
        self.is_running: bool = False
        self.is_paused: bool = False
        self._task: Optional[asyncio.Task] = None
        self._drain_task: Optional[asyncio.Task] = None

        # Configuration
        self.interval_ms: int = 500  # speed between transactions
        self.feedback_delay_ms: int = 3000  # delay before verified feedback arrives
        self.fraud_regime: str = "normal"  # "normal", "historical", "drift_evasion"
        self.adaptive_learning_enabled: bool = True

        # Statistics
        self.transactions_generated: int = 0
        self.feedback_processed: int = 0
        self.fraud_count_simulated: int = 0
        self.fraud_detected_fixed: int = 0
        self.fraud_detected_adaptive: int = 0
        self.fraud_missed_fixed: int = 0
        self.fraud_missed_adaptive: int = 0

        # Queue for delayed feedback: deque of (due_timestamp, scheduled_timestamp, tx_id, ground_truth)
        self.pending_feedback: deque = deque()
        self.processed_tx_ids: set = set()

    async def start(self):
        """Start the background simulator task if not running."""
        # Cancel any active background drainer since regular loop takes over feedback processing
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
            self._drain_task = None

        if self.is_running:
            if self.is_paused:
                self.is_paused = False
                logger.info("Simulator resumed from pause.")
                await ws_manager.broadcast("simulator_status", self.get_status())
            return

        self.is_running = True
        self.is_paused = False
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Transaction simulator started.")
        await ws_manager.broadcast("simulator_status", self.get_status())

    async def pause(self):
        """Pause transaction emission while preserving state."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("Transaction simulator paused.")
            await ws_manager.broadcast("simulator_status", self.get_status())

    async def resume(self):
        """Resume paused simulation."""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("Transaction simulator resumed.")
            await ws_manager.broadcast("simulator_status", self.get_status())

    async def stop(self, wait_for_pending: bool = False):
        """
        Stop transaction generation while allowing all scheduled pending feedback to mature and verify.
        Does not discard pending feedback silently.
        """
        self.is_running = False
        self.is_paused = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

        logger.info(
            f"Transaction simulator generation stopped. In-flight pending feedback items to mature: {len(self.pending_feedback)}"
        )
        await ws_manager.broadcast("simulator_status", self.get_status())

        # If there are pending feedback items scheduled, launch background draining task to let them mature
        if self.pending_feedback:
            if self._drain_task and not self._drain_task.done():
                self._drain_task.cancel()
                try:
                    await self._drain_task
                except asyncio.CancelledError:
                    pass

            self._drain_task = asyncio.create_task(self._drain_all_pending_feedback())
            if wait_for_pending:
                await self._drain_task

    async def _drain_all_pending_feedback(self):
        """
        Drains all scheduled feedback in the pending queue until empty.
        Waits for each transaction's scheduled delay to elapse, processes the feedback,
        persists ground truth in SQLite, feeds ASW-DD drift detector, and broadcasts WebSocket events.
        """
        logger.info(f"[FEEDBACK PIPELINE] Background feedback drainer started for {len(self.pending_feedback)} pending items.")
        try:
            while self.pending_feedback:
                next_due = self.pending_feedback[0][0]
                now = time.time()
                wait_sec = max(0.0, next_due - now)
                if wait_sec > 0:
                    await asyncio.sleep(min(wait_sec, 0.2))

                # Process mature items
                db = SessionLocal()
                try:
                    processed = await self._process_mature_feedback(db)
                    if processed > 0:
                        await ws_manager.broadcast("simulator_status", self.get_status())
                except Exception as e:
                    logger.error(f"[FEEDBACK PIPELINE] Error during feedback drain: {e}", exc_info=True)
                finally:
                    db.close()

            logger.info(
                f"[FEEDBACK PIPELINE] Feedback drainer completed. All pending items verified. "
                f"Total Generated={self.transactions_generated}, Total Processed={self.feedback_processed}."
            )
            await ws_manager.broadcast("simulator_status", self.get_status())
        except asyncio.CancelledError:
            logger.info("[FEEDBACK PIPELINE] Feedback drainer task cancelled.")
        except Exception as err:
            logger.error(f"[FEEDBACK PIPELINE] Unexpected error in feedback drainer: {err}", exc_info=True)

    async def wait_for_pending_feedback(self, timeout: float = 15.0):
        """Helper for tests or synchronous workflows to wait until all pending feedback is drained."""
        start_time = time.time()
        while self.pending_feedback or (self._drain_task and not self._drain_task.done()):
            if time.time() - start_time > timeout:
                logger.warning(f"wait_for_pending_feedback timed out after {timeout}s.")
                break
            await asyncio.sleep(0.1)

    async def cancel_pending_feedback(self) -> int:
        """
        Explicitly cancels any unverified pending feedback items in the queue,
        marking their database records as cancelled rather than leaving them in a silent limbo.
        """
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()
            self._drain_task = None

        cancelled_count = 0
        db = SessionLocal()
        try:
            while self.pending_feedback:
                _, _, tx_id, _ = self.pending_feedback.popleft()
                if tx_id in self.processed_tx_ids:
                    continue
                self.processed_tx_ids.add(tx_id)
                db_tx = db.query(DBTransaction).filter(DBTransaction.tx_id == tx_id).first()
                if db_tx and not db_tx.feedback_received:
                    db_tx.feedback_received = False
                    db_tx.feedback_label = -1  # Explicit sentinel for CANCELLED
                    db_tx.feedback_timestamp = datetime.now(timezone.utc)
                    cancelled_count += 1
            db.commit()
            logger.info(f"[FEEDBACK PIPELINE] Explicitly cancelled {cancelled_count} pending feedback items.")
        except Exception as e:
            db.rollback()
            logger.error(f"[FEEDBACK PIPELINE] Error cancelling pending feedback: {e}", exc_info=True)
        finally:
            db.close()

        await ws_manager.broadcast("simulator_status", self.get_status())
        return cancelled_count

    def reset(self):
        """Reset simulator statistics and pending feedback queue."""
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()
            self._drain_task = None
        self.transactions_generated = 0
        self.feedback_processed = 0
        self.fraud_count_simulated = 0
        self.fraud_detected_fixed = 0
        self.fraud_detected_adaptive = 0
        self.fraud_missed_fixed = 0
        self.fraud_missed_adaptive = 0
        self.pending_feedback.clear()
        self.processed_tx_ids.clear()
        logger.info("Transaction simulator statistics and queues reset.")

    def update_config(
        self,
        interval_ms: Optional[int] = None,
        feedback_delay_ms: Optional[int] = None,
        fraud_regime: Optional[str] = None,
        adaptive_learning_enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update simulator operational parameters."""
        if interval_ms is not None:
            self.interval_ms = max(50, min(10000, interval_ms))
        if feedback_delay_ms is not None:
            self.feedback_delay_ms = max(200, min(30000, feedback_delay_ms))
        if fraud_regime is not None:
            if fraud_regime in ["normal", "historical", "drift_evasion"]:
                self.fraud_regime = fraud_regime
            else:
                raise ValueError(f"Unknown fraud regime: {fraud_regime}")
        if adaptive_learning_enabled is not None:
            self.adaptive_learning_enabled = adaptive_learning_enabled

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Return live simulator status and counters."""
        can_rollback = False
        if adaptive_service.adaptive_model and adaptive_service.last_stable_model:
            if adaptive_service.last_stable_version_tag != adaptive_service.adaptive_model.version_tag:
                can_rollback = True

        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "fraud_regime": self.fraud_regime,
            "interval_ms": self.interval_ms,
            "feedback_delay_ms": self.feedback_delay_ms,
            "adaptive_learning_enabled": self.adaptive_learning_enabled,
            "transactions_generated": self.transactions_generated,
            "feedback_processed": self.feedback_processed,
            "pending_feedback_count": len(self.pending_feedback),
            "fraud_count_simulated": self.fraud_count_simulated,
            "fraud_detected_fixed": self.fraud_detected_fixed,
            "fraud_detected_adaptive": self.fraud_detected_adaptive,
            "fraud_missed_fixed": self.fraud_missed_fixed,
            "fraud_missed_adaptive": self.fraud_missed_adaptive,
            "active_adaptive_version": adaptive_service.adaptive_model.version_tag if adaptive_service.adaptive_model else "unknown",
            "can_rollback": can_rollback
        }

    async def _process_mature_feedback(self, db) -> int:
        """
        Process all scheduled delayed feedback items whose due time has expired.
        Updates transaction records with ground truth, feeds error signal to drift detector,
        and broadcasts verified feedback events over WebSockets.
        """
        current_time = time.time()
        processed_count = 0

        while self.pending_feedback and self.pending_feedback[0][0] <= current_time:
            due_time, scheduled_time, mature_tx_id, mature_label = self.pending_feedback.popleft()

            # Prevent duplicate feedback processing
            if mature_tx_id in self.processed_tx_ids:
                logger.warning(f"[FEEDBACK PIPELINE] Duplicate feedback skipped for tx_id={mature_tx_id}")
                continue
            self.processed_tx_ids.add(mature_tx_id)

            actual_processing_time = time.time()
            sched_iso = datetime.fromtimestamp(scheduled_time, timezone.utc).isoformat()
            due_iso = datetime.fromtimestamp(due_time, timezone.utc).isoformat()
            proc_iso = datetime.fromtimestamp(actual_processing_time, timezone.utc).isoformat()
            actual_delay_sec = actual_processing_time - scheduled_time

            logger.info(
                f"[FEEDBACK PIPELINE] Executing mature feedback: tx_id={mature_tx_id} | "
                f"Ground Truth={mature_label} | "
                f"Scheduled={sched_iso} | Due={due_iso} | Processed={proc_iso} | "
                f"Actual Delay={actual_delay_sec:.2f}s (Configured: {self.feedback_delay_ms / 1000.0:.1f}s)"
            )

            try:
                # 1. Process feedback with adaptive learning service
                fb_res = adaptive_service.process_verified_feedback(
                    mature_tx_id,
                    mature_label,
                    db
                )
                self.feedback_processed += 1
                processed_count += 1

                # 2. Query updated database record to confirm persistence
                mature_tx = db.query(DBTransaction).filter(DBTransaction.tx_id == mature_tx_id).first()
                fixed_pred = mature_tx.fixed_prediction if mature_tx else 0
                adaptive_pred = fb_res["prediction"]
                adaptive_err = 0 if adaptive_pred == mature_label else 1
                fixed_err = 0 if fixed_pred == mature_label else 1

                db_status = "CONFIRMED_PERSISTED" if (mature_tx and mature_tx.feedback_received) else "NOT_PERSISTED"
                logger.info(
                    f"[FEEDBACK PIPELINE] DB update result for tx_id={mature_tx_id}: "
                    f"status={db_status} | feedback_received={getattr(mature_tx, 'feedback_received', None)} | "
                    f"feedback_label={getattr(mature_tx, 'feedback_label', None)} | "
                    f"feedback_timestamp={getattr(mature_tx, 'feedback_timestamp', None)}"
                )

                logger.info(
                    f"[FEEDBACK PIPELINE] Adaptive learning response for tx_id={mature_tx_id}: "
                    f"adaptive_pred={adaptive_pred} (correct={fb_res['prediction_correct']}) | "
                    f"fixed_pred={fixed_pred} | "
                    f"drift_severity={fb_res['drift_status']['severity']} (score={fb_res['drift_status']['drift_score']:.4f}, "
                    f"curr_err={fb_res['drift_status']['current_error_rate']:.4f}, "
                    f"ref_err={fb_res['drift_status']['reference_error_rate']:.4f}) | "
                    f"learning_action={fb_res['learning_action_triggered']}"
                )

                # 3. Broadcast verified feedback event over WebSocket
                ws_feedback_event = {
                    "tx_id": mature_tx_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ground_truth": mature_label,
                    "adaptive_prediction": adaptive_pred,
                    "fixed_prediction": fixed_pred,
                    "adaptive_error": adaptive_err,
                    "fixed_error": fixed_err,
                    "prediction": adaptive_pred,
                    "prediction_correct": fb_res["prediction_correct"],
                    "drift_status": fb_res["drift_status"],
                    "learning_action": fb_res["learning_action_triggered"]
                }
                try:
                    await ws_manager.broadcast("verified_feedback", ws_feedback_event)
                    logger.info(f"[FEEDBACK PIPELINE] WebSocket broadcast SUCCESS for verified_feedback (tx_id={mature_tx_id})")
                except Exception as ws_err:
                    logger.error(f"[FEEDBACK PIPELINE] WebSocket broadcast FAILED for verified_feedback (tx_id={mature_tx_id}): {ws_err}")

                # 4. If concept drift detected, broadcast drift alert
                if fb_res["drift_status"]["drift_detected"]:
                    try:
                        await ws_manager.broadcast("drift_alert", fb_res["drift_status"])
                        logger.info(f"[FEEDBACK PIPELINE] WebSocket drift_alert broadcast SUCCESS (tx_id={mature_tx_id})")
                    except Exception as ws_err:
                        logger.error(f"[FEEDBACK PIPELINE] WebSocket drift_alert broadcast FAILED: {ws_err}")

                # 5. If model update occurred (promoted/rejected), broadcast model update
                if fb_res["learning_action_triggered"] in ["promoted", "rejected"]:
                    try:
                        await ws_manager.broadcast("model_update", {
                            "action": fb_res["learning_action_triggered"],
                            "active_version": adaptive_service.adaptive_model.version_tag
                        })
                        logger.info(f"[FEEDBACK PIPELINE] WebSocket model_update broadcast SUCCESS (tx_id={mature_tx_id})")
                    except Exception as ws_err:
                        logger.error(f"[FEEDBACK PIPELINE] WebSocket model_update broadcast FAILED: {ws_err}")

            except Exception as fb_err:
                logger.error(f"[FEEDBACK PIPELINE] EXCEPTION processing feedback for tx_id={mature_tx_id}: {fb_err}", exc_info=True)
                db.rollback()

        return processed_count

    async def _run_loop(self):
        """Continuous simulation loop."""
        cust_id_pool = [f"CUST_{i:04d}" for i in range(1, 201)]

        while self.is_running:
            try:
                db = SessionLocal()
                try:
                    # 1. ALWAYS process any mature feedback regardless of whether transaction emission is paused
                    await self._process_mature_feedback(db)

                    # 2. If paused, wait briefly and loop back to allow pending feedback to continue maturing
                    if self.is_paused:
                        db.close()
                        await asyncio.sleep(0.2)
                        continue

                    # 3. Generate transaction based on current regime
                    now = datetime.now(timezone.utc)
                    cust_id = self.generator.rng.choice(cust_id_pool)

                    if self.fraud_regime == "normal":
                        tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)
                    elif self.fraud_regime == "historical":
                        is_fraud = self.generator.rng.random() < 0.12
                        if is_fraud:
                            tx_dict = self.generator.generate_historical_fraud_transaction(cust_id, now)
                        else:
                            tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)
                    elif self.fraud_regime == "drift_evasion":
                        is_fraud = self.generator.rng.random() < 0.18
                        if is_fraud:
                            tx_dict = self.generator.generate_drift_fraud_transaction(cust_id, now)
                        else:
                            tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)
                    else:
                        tx_dict = self.generator.generate_legitimate_transaction(cust_id, now)

                    tx_id = f"TX_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6].upper()}"
                    tx_dict["tx_id"] = tx_id
                    ground_truth = tx_dict["is_fraud"]

                    # 4. Score with ML Models (NO ground truth passed to model weights)
                    pred_res = adaptive_service.predict_transaction(tx_dict, db)
                    self.transactions_generated += 1

                    fixed_pred = pred_res["fixed_prediction"]
                    adaptive_pred = pred_res["adaptive_prediction"]

                    if ground_truth == 1:
                        self.fraud_count_simulated += 1
                        if fixed_pred == 1:
                            self.fraud_detected_fixed += 1
                        else:
                            self.fraud_missed_fixed += 1

                        if adaptive_pred == 1:
                            self.fraud_detected_adaptive += 1
                        else:
                            self.fraud_missed_adaptive += 1

                    # 5. Schedule Delayed Feedback (feedback arrives after configured delay)
                    scheduled_timestamp = time.time()
                    due_timestamp = scheduled_timestamp + (self.feedback_delay_ms / 1000.0)
                    self.pending_feedback.append((due_timestamp, scheduled_timestamp, tx_id, ground_truth))

                    logger.info(
                        f"[FEEDBACK PIPELINE] Scheduled delayed feedback: tx_id={tx_id} | "
                        f"Ground Truth={ground_truth} | "
                        f"Scheduled At={datetime.fromtimestamp(scheduled_timestamp, timezone.utc).isoformat()} | "
                        f"Due At={datetime.fromtimestamp(due_timestamp, timezone.utc).isoformat()} | "
                        f"Delay={self.feedback_delay_ms}ms | Pending Queue Size={len(self.pending_feedback)}"
                    )

                    # 6. Broadcast new transaction event over WebSocket (Ground-truth is HIDDEN!)
                    public_tx_event = {
                        "tx_id": pred_res["tx_id"],
                        "timestamp": pred_res["timestamp"].isoformat() if hasattr(pred_res["timestamp"], "isoformat") else str(pred_res["timestamp"]),
                        "amount": pred_res["amount"],
                        "merchant_category": pred_res["merchant_category"],
                        "distance_from_home": pred_res["distance_from_home"],
                        "foreign_transaction": pred_res["foreign_transaction"],
                        "velocity_1h": pred_res["velocity_1h"],
                        "device_trust_score": pred_res["device_trust_score"],
                        "fixed_prediction": fixed_pred,
                        "fixed_score": pred_res["fixed_score"],
                        "adaptive_prediction": adaptive_pred,
                        "adaptive_score": pred_res["adaptive_score"],
                        "adaptive_version": pred_res["adaptive_version"],
                        "feedback_status": "pending"
                    }
                    await ws_manager.broadcast("new_transaction", public_tx_event)

                except Exception as inner_e:
                    db.rollback()
                    raise inner_e
                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Simulator error in loop: {e}", exc_info=True)

            await asyncio.sleep(self.interval_ms / 1000.0)

# Global simulator instance
simulator = TransactionSimulator()
