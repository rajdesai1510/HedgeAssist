"""
Volatility forecasting model using machine learning.

This module provides a Random Forest-based volatility forecasting model that
predicts future volatility based on historical price data. The model uses
technical indicators and statistical features to forecast volatility for
risk management and hedging decisions.

Key Features:
- Random Forest regression for volatility prediction
- Feature engineering with rolling statistics
- Model persistence and loading
- Real-time volatility forecasting

Mathematical Features:
- Rolling volatility (standard deviation of returns)
- Moving averages for trend analysis
- Momentum indicators for price movement
- Log returns for stationarity

Author: Crypto Portfolio Risk Management Team
Version: 2.0.0
License: MIT
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
from typing import List, Optional, Tuple
from loguru import logger

class VolatilityForecaster:
    """
    Machine learning model for volatility forecasting.
    
    This class implements a Random Forest-based volatility forecasting model
    that predicts future volatility based on historical price data. The model
    uses technical indicators and statistical features to provide accurate
    volatility predictions for risk management applications.
    
    The model is trained on features including:
    - Rolling volatility (standard deviation of log returns)
    - Moving averages of prices
    - Momentum indicators
    - Historical volatility patterns
    
    Attributes:
        model_path (str): Path to saved model file
        model (RandomForestRegressor): Trained Random Forest model
        feature_names (List[str]): Names of features used in training
    """
    
    def __init__(self, model_path: str = 'ml/vol_model.pkl'):
        """
        Initialize the volatility forecaster.
        
        Args:
            model_path (str): Path to saved model file (default: 'ml/vol_model.pkl')
        """
        self.model_path = model_path
        self.model = RandomForestRegressor(
            n_estimators=100,  # Number of trees in the forest
            random_state=42,   # For reproducible results
            max_depth=10,      # Maximum depth of trees
            min_samples_split=5,  # Minimum samples required to split
            min_samples_leaf=2    # Minimum samples required at leaf node
        )
        self.feature_names = ['ma', 'momentum']  # Feature names for interpretability
        
        # Load pre-trained model if available
        if os.path.exists(self.model_path):
            self.load()
            logger.info(f"Loaded pre-trained volatility model from {self.model_path}")
        else:
            logger.info("No pre-trained model found. Model will be trained when fit() is called.")

    def _prepare_features(self, prices: List[float], window: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features for volatility forecasting.
        
        This method transforms raw price data into features suitable for
        machine learning. It calculates rolling statistics and technical
        indicators that are predictive of future volatility.
        
        Args:
            prices (List[float]): Historical price data
            window (int): Rolling window size for calculations (default: 20)
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Features (X) and targets (y) arrays
            
        Raises:
            ValueError: If prices list is too short for window size
        """
        try:
            if len(prices) < window + 1:
                raise ValueError(f"Price data too short. Need at least {window + 1} points, got {len(prices)}")
            
            # Calculate log returns for stationarity
            returns = np.diff(np.log(prices))
            
            # Create DataFrame for feature engineering
            df = pd.DataFrame({'returns': returns})
            
            # Calculate rolling volatility (target variable)
            df['volatility'] = df['returns'].rolling(window).std()
            
            # Calculate moving average of prices (feature)
            df['ma'] = pd.Series(prices[:-1]).rolling(window).mean()
            
            # Calculate momentum indicator (feature)
            df['momentum'] = df['returns'].rolling(window).mean()
            
            # Remove NaN values from rolling calculations
            df = df.dropna()
            
            # Prepare features and target
            X = df[['ma', 'momentum']].values
            y = df['volatility'].values
            
            logger.debug(f"Prepared {len(X)} samples with {X.shape[1]} features")
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            raise

    def fit(self, prices: List[float], window: int = 20) -> None:
        """
        Train the volatility forecasting model.
        
        This method trains the Random Forest model on historical price data
        to learn patterns that predict future volatility. The model learns
        the relationship between technical indicators and realized volatility.
        
        Args:
            prices (List[float]): Historical price data for training
            window (int): Rolling window size for feature calculation (default: 20)
            
        Raises:
            ValueError: If insufficient data for training
            Exception: If training fails
        """
        try:
            logger.info(f"Training volatility model on {len(prices)} price points")
            
            # Prepare features and targets
            X, y = self._prepare_features(prices, window)
            
            if len(X) < 50:  # Minimum samples for reliable training
                raise ValueError(f"Insufficient data for training. Need at least 50 samples, got {len(X)}")
            
            # Train the Random Forest model
            self.model.fit(X, y)
            
            # Save the trained model
            self.save()
            
            logger.info(f"Volatility model trained successfully. Model saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error training volatility model: {e}")
            raise

    def predict(self, prices: List[float], window: int = 20) -> Optional[float]:
        """
        Predict future volatility based on recent price data.
        
        This method uses the trained model to predict the next period's
        volatility based on recent price movements and technical indicators.
        
        Args:
            prices (List[float]): Recent price data for prediction
            window (int): Rolling window size for feature calculation (default: 20)
            
        Returns:
            Optional[float]: Predicted volatility value, or None if prediction fails
            
        Raises:
            ValueError: If insufficient data for prediction
        """
        try:
            if len(prices) < window + 1:
                raise ValueError(f"Insufficient data for prediction. Need at least {window + 1} points, got {len(prices)}")
            
            # Prepare features for prediction
            X, _ = self._prepare_features(prices, window)
            
            if len(X) == 0:
                logger.warning("No features available for prediction")
                return None
            
            # Make prediction using the most recent features
            prediction = float(self.model.predict([X[-1]])[0])
            
            logger.debug(f"Predicted volatility: {prediction:.4f}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting volatility: {e}")
            return None

    def save(self) -> None:
        """
        Save the trained model to disk.
        
        This method persists the trained Random Forest model to the specified
        file path for later loading and use.
        
        Raises:
            Exception: If model saving fails
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Save the model using joblib
            joblib.dump(self.model, self.model_path)
            
            logger.debug(f"Model saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise

    def load(self) -> None:
        """
        Load a trained model from disk.
        
        This method loads a previously trained model from the specified
        file path for immediate use without retraining.
        
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            # Load the model using joblib
            self.model = joblib.load(self.model_path)
            
            logger.debug(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def get_feature_importance(self) -> Optional[dict]:
        """
        Get feature importance scores from the trained model.
        
        This method returns the importance scores for each feature used
        in the model, providing insights into which factors are most
        predictive of volatility.
        
        Returns:
            Optional[dict]: Dictionary mapping feature names to importance scores,
                          or None if model is not trained
        """
        try:
            if not hasattr(self.model, 'feature_importances_'):
                logger.warning("Model not trained yet. Cannot get feature importance.")
                return None
            
            importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
            
            logger.debug(f"Feature importance: {importance_dict}")
            return importance_dict
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return None
    
    def evaluate_model(self, test_prices: List[float], window: int = 20) -> Optional[dict]:
        """
        Evaluate model performance on test data.
        
        This method calculates performance metrics for the trained model
        using test data, including mean squared error and R-squared score.
        
        Args:
            test_prices (List[float]): Test price data for evaluation
            window (int): Rolling window size for feature calculation (default: 20)
            
        Returns:
            Optional[dict]: Dictionary containing evaluation metrics,
                          or None if evaluation fails
        """
        try:
            from sklearn.metrics import mean_squared_error, r2_score
            
            # Prepare test features and targets
            X_test, y_test = self._prepare_features(test_prices, window)
            
            if len(X_test) == 0:
                logger.warning("No test data available for evaluation")
                return None
            
            # Make predictions on test data
            y_pred = self.model.predict(X_test)
            
            # Calculate metrics
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            metrics = {
                'mean_squared_error': mse,
                'r2_score': r2,
                'rmse': np.sqrt(mse),
                'test_samples': len(y_test)
            }
            
            logger.info(f"Model evaluation - MSE: {mse:.6f}, R²: {r2:.4f}, RMSE: {np.sqrt(mse):.4f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return None 