import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Tuple, Dict, Any, Optional

CATEGORIES = ["retail", "grocery", "luxury", "crypto", "electronics", "travel", "dining", "gaming"]

class SyntheticDatasetGenerator:
    """
    Generates realistic synthetic financial transactions simulating normal behavior
    and two distinct fraud regimes:
      1. Historical Fraud Regime: High amount, luxury/crypto, foreign, high distance.
      2. Changed Strategy Regime (Concept Drift): Micro-amounts ($12-$48), domestic,
         disguised categories (gaming/retail/dining), high velocity (5-14/hr), off-peak hours.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def generate_legitimate_transaction(
        self,
        customer_id: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Generate a legitimate transaction consistent with regular cardholder behavior."""
        hour = timestamp.hour
        # Mostly daytime (8 to 22), occasional evening
        amount = float(self.rng.gamma(shape=2.5, scale=25.0) + 5.0)  # ~$20 - $150
        amount = round(min(amount, 450.0), 2)
        
        # Legitimate merchants mostly grocery, retail, dining, travel
        cat_probs = [0.30, 0.35, 0.02, 0.01, 0.05, 0.05, 0.20, 0.02]
        merchant_cat = self.rng.choice(CATEGORIES, p=cat_probs)
        
        # Legitimate features: local, trusted device, low velocity
        distance = round(float(self.rng.exponential(scale=8.0)), 2)
        foreign = 1 if self.rng.random() < 0.03 else 0
        new_device = 1 if self.rng.random() < 0.05 else 0
        device_trust = round(float(self.rng.uniform(0.75, 1.0) if new_device == 0 else self.rng.uniform(0.50, 0.80)), 4)
        velocity_1h = int(self.rng.choice([1, 2, 3], p=[0.85, 0.12, 0.03]))
        ip_risk = round(float(self.rng.beta(a=1, b=10)), 4)  # typically very low (0.01 - 0.15)

        return {
            "customer_id": customer_id,
            "timestamp": timestamp.isoformat(),
            "amount": amount,
            "tx_hour": hour,
            "velocity_1h": velocity_1h,
            "distance_from_prev": distance,
            "new_device": new_device,
            "merchant_category": merchant_cat,
            "foreign_transaction": foreign,
            "device_trust_score": device_trust,
            "ip_risk_score": ip_risk,
            "is_fraud": 0,
            "fraud_regime": "none",
            "pattern_type": "standard_legitimate"
        }

    def generate_historical_fraud_transaction(
        self,
        customer_id: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Regime 1: Historical fraud pattern.
        Characterized by: large amounts, luxury/crypto/electronics, foreign location, new device.
        """
        hour = timestamp.hour
        amount = float(self.rng.uniform(650.0, 3200.0))
        amount = round(amount, 2)
        
        cat_probs = [0.05, 0.02, 0.40, 0.30, 0.15, 0.06, 0.01, 0.01]
        merchant_cat = self.rng.choice(CATEGORIES, p=cat_probs)
        
        distance = round(float(self.rng.uniform(150.0, 2500.0)), 2)
        foreign = 1 if self.rng.random() < 0.65 else 0
        new_device = 1 if self.rng.random() < 0.85 else 0
        device_trust = round(float(self.rng.uniform(0.05, 0.35)), 4)
        velocity_1h = int(self.rng.choice([2, 3, 4], p=[0.5, 0.35, 0.15]))
        ip_risk = round(float(self.rng.uniform(0.60, 0.98)), 4)

        return {
            "customer_id": customer_id,
            "timestamp": timestamp.isoformat(),
            "amount": amount,
            "tx_hour": hour,
            "velocity_1h": velocity_1h,
            "distance_from_prev": distance,
            "new_device": new_device,
            "merchant_category": merchant_cat,
            "foreign_transaction": foreign,
            "device_trust_score": device_trust,
            "ip_risk_score": ip_risk,
            "is_fraud": 1,
            "fraud_regime": "historical",
            "pattern_type": "historical_high_ticket_foreign"
        }

    def generate_drift_fraud_transaction(
        self,
        customer_id: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Regime 2: Changed fraud strategy (Concept Drift / Evasion Attack).
        Fraudsters adapt to evade amount, foreign, and IP risk rules:
        - Micro amounts ($12 - $48) to bypass amount thresholds
        - Domestic and local (distance 1-15 miles)
        - Everyday merchant categories: retail, dining, gaming, grocery
        - Residential proxy / cookie theft: low IP risk (0.10 - 0.30), high device trust (0.75 - 0.90)
        - The EVASION SIGNATURE: High velocity burst (6 to 15 transactions/hr) and nocturnal timing (1 AM - 5 AM).
        Because the historical model weighted amount and foreign location heavily,
        it fails completely to catch this micro-velocity nocturnal fraud.
        """
        hour = int(self.rng.choice([1, 2, 3, 4, 5]))
        amount = round(float(self.rng.uniform(14.0, 48.50)), 2)
        
        # Everyday categories to bypass luxury/crypto filters
        cat_probs = [0.35, 0.20, 0.00, 0.00, 0.05, 0.05, 0.25, 0.10]
        merchant_cat = self.rng.choice(CATEGORIES, p=cat_probs)
        
        distance = round(float(self.rng.uniform(1.0, 12.0)), 2)
        foreign = 0  # domestic to evade rule
        new_device = 0  # hijacked session / stolen cookie looks like known device
        device_trust = round(float(self.rng.uniform(0.72, 0.92)), 4)
        velocity_1h = int(self.rng.integers(low=6, high=16))
        ip_risk = round(float(self.rng.uniform(0.08, 0.28)), 4)  # residential IP pool

        return {
            "customer_id": customer_id,
            "timestamp": timestamp.isoformat(),
            "amount": amount,
            "tx_hour": hour,
            "velocity_1h": velocity_1h,
            "distance_from_prev": distance,
            "new_device": new_device,
            "merchant_category": merchant_cat,
            "foreign_transaction": foreign,
            "device_trust_score": device_trust,
            "ip_risk_score": ip_risk,
            "is_fraud": 1,
            "fraud_regime": "drift_evasion",
            "pattern_type": "drift_micro_velocity_burst"
        }

    def generate_dataset(
        self,
        total_samples: int = 12000,
        historical_ratio: float = 0.60,
        historical_fraud_rate: float = 0.08,
        drift_fraud_rate: float = 0.14,
        start_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Generate complete chronological dataset containing both regimes.
        
        Historical period: samples from 0 up to total_samples * historical_ratio.
        Drift period: samples from historical split to the end.
        """
        if start_time is None:
            start_time = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

        current_time = start_time
        records = []
        customer_pool = [f"CUST_{i:04d}" for i in range(1, 501)]
        
        num_historical = int(total_samples * historical_ratio)
        num_drift = total_samples - num_historical

        # --- Period 1: Historical Regime ---
        for i in range(num_historical):
            current_time += timedelta(seconds=int(self.rng.integers(15, 120)))
            cust = self.rng.choice(customer_pool)
            
            is_fraud = self.rng.random() < historical_fraud_rate
            if is_fraud:
                tx = self.generate_historical_fraud_transaction(cust, current_time)
            else:
                tx = self.generate_legitimate_transaction(cust, current_time)
            
            tx["tx_id"] = f"TX_HIST_{i+1:06d}"
            records.append(tx)

        # --- Period 2: Drift Regime (Changed Fraud Strategy) ---
        for j in range(num_drift):
            current_time += timedelta(seconds=int(self.rng.integers(15, 120)))
            cust = self.rng.choice(customer_pool)
            
            is_fraud = self.rng.random() < drift_fraud_rate
            if is_fraud:
                tx = self.generate_drift_fraud_transaction(cust, current_time)
            else:
                tx = self.generate_legitimate_transaction(cust, current_time)
            
            tx["tx_id"] = f"TX_DRIFT_{j+1:06d}"
            records.append(tx)

        df = pd.DataFrame(records)
        return df

    def save_dataset_to_csv(self, df: pd.DataFrame, filepath: str) -> str:
        """Save dataset to specified CSV file."""
        df.to_csv(filepath, index=False)
        return filepath
