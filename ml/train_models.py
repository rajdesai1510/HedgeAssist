import numpy as np
from volatility_model import VolatilityForecaster
from hedge_timing_model import HedgeTimingClassifier

# Example: Use a sample BTC price list (replace with real data if available)
btc_prices = [
    30000, 30100, 30250, 30300, 30200, 30150, 30220, 30350, 30400, 30500,
    30600, 30700, 30800, 30750, 30850, 30900, 31000, 31100, 31200, 31300,
    31250, 31350, 31400, 31500, 31600, 31700, 31800, 31900, 32000, 32100,
    32200, 32300, 32400, 32500, 32600, 32700, 32800, 32900, 33000, 33100,
    33200, 33300, 33400, 33500, 33600, 33700, 33800, 33900, 34000, 34100
]

# Train volatility forecaster
vol_model = VolatilityForecaster()
vol_model.fit(btc_prices, window=10)
print("Volatility model trained and saved.")

# Generate synthetic data for hedge timing model
# Features: [volatility, abs(position.size), time since last hedge (seconds), delta]
# Labels: 1=hedge, 0=wait
np.random.seed(42)
X = []
y = []
for i in range(100):
    vol = np.random.uniform(0.01, 0.1)
    size = np.random.uniform(1, 100)
    time_since = np.random.uniform(0, 3600)
    delta = np.random.uniform(-1, 1)
    label = 1 if (vol > 0.05 and abs(delta) > 0.5 and time_since > 600) else 0
    X.append([vol, size, time_since, delta])
    y.append(label)
X = np.array(X)
y = np.array(y)

hedge_model = HedgeTimingClassifier()
hedge_model.fit(X, y)
print("Hedge timing model trained and saved.") 