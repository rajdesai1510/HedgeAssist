"""
Hedge timing classifier using machine learning.

This module provides a Random Forest-based classifier that determines the optimal
timing for executing hedging operations. The model analyzes various market
conditions and position characteristics to predict whether it's optimal to
hedge now or wait for better conditions.

Key Features:
- Random Forest classification for hedge timing decisions
- Multi-feature analysis including volatility, position size, and market conditions
- Binary classification (hedge now vs. wait)
- Model persistence and real-time predictions

Features Analyzed:
- Current volatility levels
- Position size and exposure
- Time since last hedge
- Delta exposure
- Market momentum
- Risk metrics

Author: Crypto Portfolio Risk Management Team
Version: 2.0.0
License: MIT
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

class HedgeTimingClassifier:
    """
    Machine learning classifier for optimal hedge timing.
    
    This class implements a Random Forest-based classifier that determines
    the optimal timing for executing hedging operations. The model analyzes
    various market conditions, position characteristics, and risk metrics
    to make binary decisions: hedge now (1) or wait (0).
    
    The classifier considers multiple features:
    - Current volatility vs. historical volatility
    - Position size and delta exposure
    - Time elapsed since last hedge
    - Market momentum and trend indicators
    - Risk metric thresholds
    
    Attributes:
        model_path (str): Path to saved model file
        model (RandomForestClassifier): Trained Random Forest classifier
        scaler (StandardScaler): Feature scaler for normalization
        feature_names (List[str]): Names of features used in training
        last_hedge_times (Dict[str, datetime]): Track last hedge time per asset
    """
    
    def __init__(self, model_path: str = 'ml/hedge_timing_model.pkl'):
        """
        Initialize the hedge timing classifier.
        
        Args:
            model_path (str): Path to saved model file (default: 'ml/hedge_timing_model.pkl')
        """
        self.model_path = model_path
        self.model = RandomForestClassifier(
            n_estimators=100,    # Number of trees in the forest
            random_state=42,     # For reproducible results
            max_depth=8,         # Maximum depth of trees
            min_samples_split=10, # Minimum samples required to split
            min_samples_leaf=5,   # Minimum samples required at leaf node
            class_weight='balanced'  # Handle class imbalance
        )
        self.scaler = StandardScaler()
        self.feature_names = [
            'volatility', 'position_size', 'delta_exposure', 
            'time_since_hedge', 'market_momentum', 'risk_level'
        ]
        self.last_hedge_times = {}  # Track last hedge time per asset
        
        # Load pre-trained model if available
        if os.path.exists(self.model_path):
            self.load()
            logger.info(f"Loaded pre-trained hedge timing model from {self.model_path}")
        else:
            logger.info("No pre-trained model found. Model will be trained when fit() is called.")

    def _prepare_features(self, features_dict: Dict[str, Any]) -> np.ndarray:
        """
        Prepare features for hedge timing classification.
        
        This method transforms raw feature data into a normalized feature
        vector suitable for the machine learning classifier.
        
        Args:
            features_dict (Dict[str, Any]): Dictionary containing feature values
                - volatility: Current volatility level
                - position_size: Size of the position
                - delta_exposure: Current delta exposure
                - time_since_hedge: Hours since last hedge
                - market_momentum: Market momentum indicator
                - risk_level: Risk level indicator
                
        Returns:
            np.ndarray: Normalized feature vector
            
        Raises:
            ValueError: If required features are missing
        """
        try:
            # Extract features in the correct order
            features = []
            for feature_name in self.feature_names:
                if feature_name not in features_dict:
                    raise ValueError(f"Missing required feature: {feature_name}")
                features.append(float(features_dict[feature_name]))
            
            # Convert to numpy array and reshape for scaler
            feature_array = np.array(features).reshape(1, -1)
            
            # Normalize features if scaler is fitted
            if hasattr(self.scaler, 'mean_'):
                feature_array = self.scaler.transform(feature_array)
            
            logger.debug(f"Prepared features: {dict(zip(self.feature_names, features))}")
            return feature_array
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            raise

    def fit(self, features_list: List[Dict[str, Any]], labels: List[int]) -> None:
        """
        Train the hedge timing classifier.
        
        This method trains the Random Forest classifier on historical
        hedge timing decisions to learn patterns that indicate optimal
        hedging conditions.
        
        Args:
            features_list (List[Dict[str, Any]]): List of feature dictionaries
            labels (List[int]): Binary labels (1 = hedge now, 0 = wait)
            
        Raises:
            ValueError: If insufficient data or mismatched lengths
            Exception: If training fails
        """
        try:
            if len(features_list) != len(labels):
                raise ValueError(f"Mismatched lengths: {len(features_list)} features vs {len(labels)} labels")
            
            if len(features_list) < 100:  # Minimum samples for reliable training
                raise ValueError(f"Insufficient data for training. Need at least 100 samples, got {len(features_list)}")
            
            logger.info(f"Training hedge timing model on {len(features_list)} samples")
            
            # Prepare feature matrix
            X = []
            for features_dict in features_list:
                feature_vector = self._prepare_features(features_dict)
                X.append(feature_vector.flatten())
            
            X = np.array(X)
            y = np.array(labels)
            
            # Fit the scaler on training data
            self.scaler.fit(X)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Train the classifier
            self.model.fit(X_scaled, y)
            
            # Save the trained model
            self.save()
            
            # Log training results
            train_accuracy = self.model.score(X_scaled, y)
            logger.info(f"Hedge timing model trained successfully. Training accuracy: {train_accuracy:.4f}")
            
        except Exception as e:
            logger.error(f"Error training hedge timing model: {e}")
            raise

    def predict(self, features_dict: Dict[str, Any]) -> Optional[int]:
        """
        Predict optimal hedge timing based on current conditions.
        
        This method uses the trained classifier to determine whether
        it's optimal to hedge now (1) or wait for better conditions (0).
        
        Args:
            features_dict (Dict[str, Any]): Current feature values
                - volatility: Current volatility level
                - position_size: Size of the position
                - delta_exposure: Current delta exposure
                - time_since_hedge: Hours since last hedge
                - market_momentum: Market momentum indicator
                - risk_level: Risk level indicator
                
        Returns:
            Optional[int]: Prediction (1 = hedge now, 0 = wait), or None if prediction fails
        """
        try:
            # Prepare features
            feature_array = self._prepare_features(features_dict)
            
            # Make prediction
            prediction = int(self.model.predict(feature_array)[0])
            
            # Get prediction probability for confidence
            proba = self.model.predict_proba(feature_array)[0]
            confidence = max(proba)
            
            logger.debug(f"Hedge timing prediction: {prediction} (confidence: {confidence:.3f})")
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting hedge timing: {e}")
            return None

    def predict_with_confidence(self, features_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Predict hedge timing with confidence scores.
        
        This method provides both the prediction and confidence scores
        for more detailed analysis of the model's decision.
        
        Args:
            features_dict (Dict[str, Any]): Current feature values
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing prediction and confidence,
                                    or None if prediction fails
        """
        try:
            # Prepare features
            feature_array = self._prepare_features(features_dict)
            
            # Make prediction with probabilities
            prediction = int(self.model.predict(feature_array)[0])
            proba = self.model.predict_proba(feature_array)[0]
            
            result = {
                'prediction': prediction,
                'confidence': float(max(proba)),
                'hedge_probability': float(proba[1]),  # Probability of hedge now
                'wait_probability': float(proba[0])    # Probability of wait
            }
            
            logger.debug(f"Hedge timing prediction with confidence: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error predicting hedge timing with confidence: {e}")
            return None

    def update_last_hedge_time(self, asset: str, hedge_time: datetime = None) -> None:
        """
        Update the last hedge time for an asset.
        
        This method tracks when the last hedge was executed for each asset,
        which is used as a feature in the timing model.
        
        Args:
            asset (str): Asset symbol
            hedge_time (datetime): Time of hedge execution (default: current time)
        """
        if hedge_time is None:
            hedge_time = datetime.now()
        
        self.last_hedge_times[asset] = hedge_time
        logger.debug(f"Updated last hedge time for {asset}: {hedge_time}")

    def get_time_since_hedge(self, asset: str) -> float:
        """
        Calculate time since last hedge for an asset.
        
        Args:
            asset (str): Asset symbol
            
        Returns:
            float: Hours since last hedge, or 24.0 if no previous hedge
        """
        if asset not in self.last_hedge_times:
            return 24.0  # Default to 24 hours if no previous hedge
        
        time_diff = datetime.now() - self.last_hedge_times[asset]
        return time_diff.total_seconds() / 3600  # Convert to hours

    def save(self) -> None:
        """
        Save the trained model and scaler to disk.
        
        This method persists both the trained classifier and the feature
        scaler to the specified file path for later loading.
        
        Raises:
            Exception: If model saving fails
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Save both model and scaler
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }
            
            joblib.dump(model_data, self.model_path)
            logger.debug(f"Model and scaler saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise

    def load(self) -> None:
        """
        Load a trained model and scaler from disk.
        
        This method loads both the trained classifier and the feature
        scaler from the specified file path.
        
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            # Load model data
            model_data = joblib.load(self.model_path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            
            logger.debug(f"Model and scaler loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores from the trained model.
        
        This method returns the importance scores for each feature used
        in the model, providing insights into which factors are most
        important for hedge timing decisions.
        
        Returns:
            Optional[Dict[str, float]]: Dictionary mapping feature names to importance scores,
                                      or None if model is not trained
        """
        try:
            if not hasattr(self.model, 'feature_importances_'):
                logger.warning("Model not trained yet. Cannot get feature importance.")
                return None
            
            importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
            
            # Sort by importance
            sorted_importance = dict(sorted(importance_dict.items(), 
                                          key=lambda x: x[1], reverse=True))
            
            logger.debug(f"Feature importance: {sorted_importance}")
            return sorted_importance
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return None

    def evaluate_model(self, test_features: List[Dict[str, Any]], 
                      test_labels: List[int]) -> Optional[Dict[str, float]]:
        """
        Evaluate model performance on test data.
        
        This method calculates performance metrics for the trained model
        using test data, including accuracy, precision, recall, and F1-score.
        
        Args:
            test_features (List[Dict[str, Any]]): Test feature data
            test_labels (List[int]): Test labels
            
        Returns:
            Optional[Dict[str, float]]: Dictionary containing evaluation metrics,
                                      or None if evaluation fails
        """
        try:
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            
            if len(test_features) == 0:
                logger.warning("No test data available for evaluation")
                return None
            
            # Prepare test features
            X_test = []
            for features_dict in test_features:
                feature_vector = self._prepare_features(features_dict)
                X_test.append(feature_vector.flatten())
            
            X_test = np.array(X_test)
            y_test = np.array(test_labels)
            
            # Scale test features
            X_test_scaled = self.scaler.transform(X_test)
            
            # Make predictions
            y_pred = self.model.predict(X_test_scaled)
            
            # Calculate metrics
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, zero_division=0),
                'recall': recall_score(y_test, y_pred, zero_division=0),
                'f1_score': f1_score(y_test, y_pred, zero_division=0),
                'test_samples': len(y_test)
            }
            
            logger.info(f"Model evaluation - Accuracy: {metrics['accuracy']:.4f}, "
                       f"Precision: {metrics['precision']:.4f}, "
                       f"Recall: {metrics['recall']:.4f}, "
                       f"F1: {metrics['f1_score']:.4f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return None 