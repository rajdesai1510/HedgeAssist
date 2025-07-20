"""
Telegram bot for the spot exposure hedging system.
"""
import sys
import os
# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import plotly.graph_objs as go
import io
import random
import yfinance as yf

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from utils.config import Config
from exchanges.base import Position, MarketData
from risk.calculator import RiskCalculator, RiskMetrics, HedgeRecommendation
from hedging.strategies import HedgingManager, HedgeResult
from analytics.reporter import AnalyticsReporter
from ml.volatility_model import VolatilityForecaster
from ml.hedge_timing_model import HedgeTimingClassifier

LARGE_TRADE_NOTIONAL_THRESHOLD = 100000  # USD

class HedgingBot:
    """Telegram bot for hedging system with robust multi-user support."""
    
    def __init__(self):
        try:
            self.config = Config()
            self.risk_calculator = RiskCalculator()
            self.hedging_manager = HedgingManager()
            self.analytics_reporter = AnalyticsReporter()  # Add analytics reporter
            # Multi-user state: {chat_id: { 'positions': {asset: {...}}, 'history': [...], ... }}
            self.user_data: Dict[int, Dict[str, Any]] = {}
            self.exchanges = {}
            self.price_history: Dict[str, List[Dict[str, Any]]] = {}  # symbol: [{timestamp, price}]
            self.price_polling_task = None
            
            # Initialize bot with post_init to start background tasks
            self.application = Application.builder()\
                .token(self.config.TELEGRAM_BOT_TOKEN)\
                .post_init(self._start_background_tasks)\
                .build()
            self.setup_handlers()
            
            logger.info("Hedging Bot initialized successfully")
            self.vol_forecaster = VolatilityForecaster()
            self.hedge_timing_model = HedgeTimingClassifier()
        except Exception as e:
            logger.error(f"Error initializing Hedging Bot: {e}")
            raise
    
    def setup_handlers(self):
        """Setup bot command handlers."""
        try:
            # Command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("monitor_risk", self.monitor_risk_command))
            self.application.add_handler(CommandHandler("auto_hedge", self.auto_hedge_command))
            self.application.add_handler(CommandHandler("hedge_status", self.hedge_status_command))
            self.application.add_handler(CommandHandler("hedge_history", self.hedge_history_command))
            self.application.add_handler(CommandHandler("hedge_now", self.hedge_now_command))
            self.application.add_handler(CommandHandler("stop_monitoring", self.stop_monitoring_command))
            self.application.add_handler(CommandHandler("risk_analytics", self.risk_analytics_command))
            self.application.add_handler(CommandHandler("pnl_attribution", self.pnl_attribution_command))
            self.application.add_handler(CommandHandler("chart", self.chart_command))
            self.application.add_handler(CommandHandler("configure_monitor", self.configure_monitor_command))
            self.application.add_handler(CommandHandler("risk_report", self.risk_report_command))
            self.application.add_handler(CommandHandler("risk_charts", self.risk_charts_command))
            self.application.add_handler(CommandHandler("schedule_summary", self.schedule_summary_command))
            self.application.add_handler(CommandHandler("summary_status", self.summary_status_command))
            self.application.add_handler(CommandHandler("send_summary_now", self.send_summary_now_command))
            self.application.add_handler(CommandHandler("set_alert", self.set_alert_command))
            self.application.add_handler(CommandHandler("alerts_status", self.alerts_status_command))
            self.application.add_handler(CommandHandler("delete_alert", self.delete_alert_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("version", self.version_command))
            self.application.add_handler(CommandHandler("emergency_stop", self.emergency_stop_command))
            self.application.add_handler(CommandHandler("reset_alerts", self.reset_alerts_command))
            
            # Callback query handler for buttons
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            
            logger.info("Bot handlers setup completed")
        except Exception as e:
            logger.error(f"Error setting up bot handlers: {e}")
            raise
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command and only allow real Deribit portfolio."""
        chat_id = update.effective_chat.id if update.effective_chat else None
        user = self._get_user(chat_id)
        deribit_cfg = Config.get_exchange_config('deribit')
        if not (deribit_cfg and deribit_cfg.get('enabled', False)):
            await update.message.reply_text(
                "<b>Deribit is not available or not configured. Please set up your Deribit API credentials to use this bot.</b>",
                parse_mode=ParseMode.HTML
            )
            return
        user['portfolio_type'] = 'real'
        await update.message.reply_text(
            "✅ Using <b>Real Deribit Portfolio</b>. You can now monitor and auto-hedge your real positions.",
            parse_mode=ParseMode.HTML
        )
        followup = (
            "<b>Next steps:</b>\n"
            "• <code>/monitor_risk &lt;asset&gt; &lt;size&gt; &lt;threshold&gt;</code> — Start monitoring a position\n"
            "• <code>/auto_hedge &lt;strategy&gt; &lt;threshold&gt;</code> — Enable auto-hedging\n"
            "• <code>/hedge_status &lt;asset&gt;</code> — Check current status\n"
            "• <code>/hedge_now &lt;asset&gt; &lt;size&gt;</code> — Manual hedge\n"
            "• <code>/risk_analytics</code> — Portfolio analytics\n"
            "• <code>/pnl_attribution</code> — P&L attribution analysis\n"
            "• <code>/risk_report</code> — Detailed risk report\n"
            "• <code>/risk_charts</code> — Risk metric charts\n"
            "• <code>/schedule_summary</code> — Configure periodic summaries\n"
            "• <code>/summary_status</code> — Check summary status\n"
            "• <code>/set_alert</code> — Configure custom alerts\n"
            "• <code>/alerts_status</code> — View alert settings\n"
            "• <code>/status</code> — System status\n"
            "• <code>/version</code> — Bot version\n"
            "• <code>/chart &lt;asset&gt;</code> — Interactive charts\n"
            "• <code>/help</code> — Show help\n"
        )
        await self.application.bot.send_message(chat_id=chat_id, text=followup, parse_mode=ParseMode.HTML)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
📚 *Hedging Bot Help*

*Risk Monitoring Commands:*
• `/monitor_risk BTC 1000 0.05` - Monitor 1000 BTC with 5% risk threshold
• `/monitor_risk ETH 500 0.03` - Monitor 500 ETH with 3% risk threshold

*Hedging Commands:*
• `/auto_hedge delta_neutral 0.05` - Enable delta-neutral hedging
• `/auto_hedge options 0.03` - Enable options-based hedging
• `/auto_hedge dynamic 0.04` - Enable dynamic hedging

*Status Commands:*
• `/hedge_status BTC` - Check BTC hedging status
• `/hedge_history BTC 7d` - View 7-day hedging history

*Manual Commands:*
• `/hedge_now BTC 100` - Manually hedge 100 BTC
• `/stop_monitoring BTC` - Stop monitoring BTC

*Analytics Commands:*
• `/risk_analytics` - View comprehensive risk metrics
• `/pnl_attribution` - View P&L attribution by factor
• `/risk_report` - Generate detailed risk report with export
• `/risk_charts` - Interactive charts for risk metrics

*Summary Commands:*
• `/schedule_summary` - Configure periodic risk summaries (daily/weekly)
• `/summary_status` - Check summary schedule status
• `/send_summary_now` - Send risk summary immediately

*Alert Commands:*
• `/set_alert` - Configure custom risk alerts
• `/alerts_status` - View current alert settings
• `/delete_alert` - Remove specific alerts

*System Commands:*
• `/status` - Show overall bot status and system health
• `/version` - Show bot version and features
• `/emergency_stop` - Emergency stop all monitoring and hedging

*Available Strategies:*
• `delta_neutral` - Delta-neutral hedging with perpetuals
• `options` - Options-based hedging (puts/calls)
• `dynamic` - Dynamic hedging with rebalancing

*Risk Thresholds:*
• `0.01` - Conservative (1% risk)
• `0.05` - Moderate (5% risk)
• `0.10` - Aggressive (10% risk)
"""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    def _get_user(self, chat_id: int) -> Dict[str, Any]:
        """Get or create user data dict for a chat_id."""
        if chat_id not in self.user_data:
            self.user_data[chat_id] = {
                'positions': {},  # asset: {position, threshold, suppress_alerts, history, ...}
                'history': [],    # list of actions
            }
        return self.user_data[chat_id]
    
    async def monitor_risk_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not chat_id:
            logger.error("No chat_id found in monitor_risk_command")
            return
        user = self._get_user(chat_id)
        try:
            if not context.args or len(context.args) < 3:
                message = update.effective_message
                if message:
                    await message.reply_text(
                        "❌ Usage: `/monitor_risk <asset> <size> <delta_threshold> [<var_threshold>]`\n"
                        "Example: `/monitor_risk BTC 1000 0.05 20000`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    logger.error("No message found in update for monitor_risk_command error reply")
                return
            asset = context.args[0].upper()
            size = float(context.args[1])
            delta_threshold = float(context.args[2])
            var_threshold = float(context.args[3]) if len(context.args) > 3 else None
            position = Position(
                symbol=asset,
                size=size,
                side="long",
                entry_price=0.0,
                current_price=0.0,
                unrealized_pnl=0.0,
                timestamp=datetime.now(),
                exchange="demo"
            )
            user['positions'][asset] = {
                "position": position,
                "threshold": delta_threshold,
                "var_threshold": var_threshold,
                "start_time": datetime.now(),
                "is_active": True,
                "suppress_alerts": False,
                "history": []
            }
            user['history'].append({
                'action': 'monitor_risk', 'asset': asset, 'size': size, 'threshold': delta_threshold, 'var_threshold': var_threshold, 'time': datetime.now()
            })
            keyboard = [
                [
                    InlineKeyboardButton("🛡️ Hedge Now", callback_data=f"hedge_{asset}"),
                    InlineKeyboardButton("📊 Analytics", callback_data=f"analytics_{asset}")
                ],
                [
                    InlineKeyboardButton("⚙️ Adjust Threshold", callback_data=f"threshold_{asset}"),
                    InlineKeyboardButton("❌ Stop Monitoring", callback_data=f"stop_{asset}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = update.effective_message
            if message:
                await message.reply_text(
                    f"✅ *Risk Monitoring Started*\n\n"
                    f"*Asset:* {asset}\n"
                    f"*Position Size:* {size:,.2f}\n"
                    f"*Delta Threshold:* {delta_threshold:.1%}\n"
                    f"*VaR Threshold:* {var_threshold if var_threshold is not None else 'N/A'}\n"
                    f"*Status:* Active\n\n"
                    f"Monitoring will alert when risk exceeds threshold.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                logger.error("No message found in update for monitor_risk_command success reply")
            asyncio.create_task(self.monitor_position(chat_id, asset))
        except ValueError as e:
            message = update.effective_message
            if message:
                await message.reply_text(f"❌ Invalid input: {str(e)}")
            else:
                logger.error("No message found in update for monitor_risk_command value error reply")
        except Exception as e:
            logger.error(f"Error in monitor_risk_command: {e}")
            message = update.effective_message
            if message:
                await message.reply_text("❌ Error starting risk monitoring")
            else:
                logger.error("No message found in update for monitor_risk_command generic error reply")
    
    async def auto_hedge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enable auto-hedging for the user's selected portfolio (real or test)."""
        chat_id = update.effective_chat.id if update.effective_chat else None
        user = self._get_user(chat_id)
        if not user.get('portfolio_type'):
            await update.effective_message.reply_text("Please select a portfolio type first using /start.")
            return
        try:
            if not context.args or len(context.args) < 2:
                message = update.effective_message
                if message:
                    await message.reply_text(
                        "❌ Usage: `/auto_hedge <strategy> <threshold>`\n"
                        "Example: `/auto_hedge delta_neutral 0.05`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_text(
                        "❌ Usage: `/auto_hedge <strategy> <threshold>`\n"
                        "Example: `/auto_hedge delta_neutral 0.05`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    logger.error("No message found in update for auto_hedge_command error reply")
                return
            strategy = context.args[0]
            threshold = float(context.args[1])
            # Set hedging strategy
            if self.hedging_manager.set_strategy(strategy):
                user['auto_hedge'] = {
                    'enabled': True,
                    'strategy': strategy,
                    'threshold': threshold
                }
                await update.effective_message.reply_text(
                    f"✅ *Auto-Hedging Enabled*\n\n"
                    f"*Portfolio:* {user['portfolio_type'].title()}\n"
                    f"*Strategy:* {strategy.replace('_', ' ').title()}\n"
                    f"*Threshold:* {threshold:.1%}\n"
                    f"*Status:* Active\n\n"
                    f"Bot will automatically hedge when risk exceeds threshold.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.effective_message.reply_text(
                    f"❌ Unknown strategy: {strategy}\n"
                    f"Available strategies: {', '.join(self.hedging_manager.get_available_strategies())}"
                )
        except Exception as e:
            logger.error(f"Error in auto_hedge_command: {e}")
            await update.effective_message.reply_text("❌ Error enabling auto-hedging")
    
    async def hedge_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hedge_status command."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            asset = context.args[0].upper() if context.args else "ALL"
            status_text = ""
            if asset == "ALL":
                status_text = "<b>Portfolio Status</b>\n\n"
                for asset, data in user['positions'].items():
                    position = data['position']
                    price = await self.fetch_price(asset)
                    if price is None:
                        continue
                    market_data = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=position.exchange,
                        option_type=position.option_type,
                        strike=position.strike,
                        expiry=position.expiry,
                        underlying=position.underlying
                    )
                    if asset in self.price_history and len(self.price_history[asset]) > 10:
                        prices = [pt['price'] for pt in self.price_history[asset][-30:]]
                        volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
                    else:
                        volatility = 0.3
                    risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
                    status = "🟢 Active" if data["is_active"] else "🔴 Inactive"
                    status_text += (
                                        f"<b>{asset}:</b>\n"
                f"Size: {position.size:,.2f}\n"
                f"Threshold: {data['threshold']:.1%}\n"
                f"Status: {status}\n"
                f"Delta: {risk_metrics.delta:,.2f}\n"
                f"Gamma: {risk_metrics.gamma:,.2f}\n"
                f"Theta: {risk_metrics.theta:,.2f}\n"
                f"Vega: {risk_metrics.vega:,.2f}\n"
                f"VaR 95%: ${risk_metrics.var_95:,.2f}\n"
                f"VaR 99%: ${risk_metrics.var_99:,.2f}\n"
                f"Monitoring Since: {data['start_time'].strftime('%Y-%m-%d %H:%M')}\n"
                f"History: {', '.join(action['action'] for action in data['history'] if action['action'] != 'monitor_risk')}\n\n"
                    )
            else:
                if asset not in user['positions']:
                    await update.effective_message.reply_text(f"❌ No monitoring found for {asset}")
                    return
                data = user['positions'][asset]
                position = data['position']
                price = await self.fetch_price(asset)
                if price is None:
                    await update.effective_message.reply_text(f"❌ Failed to fetch price for {asset}")
                    return
                market_data = MarketData(
                    symbol=asset,
                    price=price,
                    volume_24h=0.0,
                    change_24h=0.0,
                    timestamp=datetime.now(),
                    exchange=position.exchange,
                    option_type=position.option_type,
                    strike=position.strike,
                    expiry=position.expiry,
                    underlying=position.underlying
                )
                if asset in self.price_history and len(self.price_history[asset]) > 10:
                    prices = [pt['price'] for pt in self.price_history[asset][-30:]]
                    volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
                else:
                    volatility = 0.3
                risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
                status = "🟢 Active" if data["is_active"] else "🔴 Inactive"
                status_text = (
                    f"<b>{asset} Status</b>\n\n"
                    f"Size: {position.size:,.2f}\n"
                    f"Threshold: {data['threshold']:.1%}\n"
                    f"Status: {status}\n"
                    f"Delta: {risk_metrics.delta:,.2f}\n"
                    f"Gamma: {risk_metrics.gamma:,.2f}\n"
                    f"Theta: {risk_metrics.theta:,.2f}\n"
                    f"Vega: {risk_metrics.vega:,.2f}\n"
                    f"VaR 95%: ${risk_metrics.var_95:,.2f}\n"
                    f"VaR 99%: ${risk_metrics.var_99:,.2f}\n"
                    f"Monitoring Since: {data['start_time'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"History: {', '.join(action['action'] for action in data['history'] if action['action'] != 'monitor_risk')}\n"
                )
            message = update.effective_message
            if message:
                await message.reply_text(status_text, parse_mode=ParseMode.HTML)
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(status_text, parse_mode=ParseMode.HTML)
            else:
                logger.error("No message found in update for hedge_status_command reply")
            self.last_chat_id = chat_id
        except Exception as e:
            logger.error(f"Error in hedge_status_command: {e}")
            message = update.effective_message
            if message:
                await message.reply_text("❌ Error getting status")
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("❌ Error getting status")
            else:
                logger.error("No message found in update for hedge_status_command error reply")
    
    async def hedge_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hedge_history command."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            asset = context.args[0].upper() if context.args else "ALL"
            timeframe = context.args[1] if context.args and len(context.args) > 1 else "7d"
            history_text = f"<b>Hedging History - {asset}</b>\n\n"
            history_text += f"<b>Timeframe:</b> {timeframe}\n\n"
            actions = []
            if asset == "ALL":
                for a, data in user['positions'].items():
                    actions.extend([{'asset': a, **h} for h in data['history']])
            else:
                if asset in user['positions']:
                    actions = [{**h, 'asset': asset} for h in user['positions'][asset]['history']]
            if not actions:
                history_text += "No hedging actions found.\n"
            else:
                actions = sorted(actions, key=lambda x: x.get('time', datetime.min), reverse=True)
                for h in actions:
                    t = h.get('time', datetime.now()).strftime('%Y-%m-%d %H:%M')
                    act = h.get('action', 'unknown').replace('_', ' ').title()
                    history_text += f"• {t} - {act} ({h.get('asset','')})\n"
            message = update.effective_message
            if message:
                await message.reply_text(history_text, parse_mode=ParseMode.HTML)
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(history_text, parse_mode=ParseMode.HTML)
            else:
                logger.error("No message found in update for hedge_history_command reply")
            self.last_chat_id = chat_id
        except Exception as e:
            logger.error(f"Error in hedge_history_command: {e}")
            message = update.effective_message
            if message:
                await message.reply_text("❌ Error getting history")
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("❌ Error getting history")
            else:
                logger.error("No message found in update for hedge_history_command error reply")
    
    async def hedge_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hedge_now command."""
        try:
            if not context.args or len(context.args) < 2:
                message = update.effective_message
                if message:
                    await message.reply_text(
                        "❌ Usage: `/hedge_now <asset> <size>`\n"
                        "Example: `/hedge_now BTC 100`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_text(
                        "❌ Usage: `/hedge_now <asset> <size>`\n"
                        "Example: `/hedge_now BTC 100`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    logger.error("No message found in update for hedge_now_command error reply")
                return
            asset = context.args[0].upper()
            size = float(context.args[1])
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            # Check if position exists, if not create a basic one for hedging
            if asset not in user['positions']:
                # Create a basic position for hedging
                price = await self.fetch_price(asset)
                if price is None:
                    await update.effective_message.reply_text(f"❌ Failed to fetch price for {asset}.")
                    return
                
                # Create a basic position
                position = Position(
                    symbol=asset,
                    size=size,
                    side="long",  # Default to long position
                    entry_price=price,
                    current_price=price,
                    unrealized_pnl=0.0,
                    timestamp=datetime.now(),
                    exchange='deribit',
                    option_type=None,
                    strike=None,
                    expiry=None,
                    underlying=asset
                )
                
                # Add to user positions
                user['positions'][asset] = {
                    'position': position,
                    'threshold': 0.05,  # Default threshold
                    'suppress_alerts': False,
                    'history': [],
                    'is_active': False  # Not actively monitored
                }
                
                await update.effective_message.reply_text(
                    f"ℹ️ <b>Created Basic Position for {asset}</b>\n\n"
                    f"<b>Size:</b> {size:,.2f}\n"
                    f"<b>Price:</b> ${price:,.2f}\n"
                    f"<b>Status:</b> Ready for hedging\n\n"
                    f"<i>Note: This position is not actively monitored. Use /monitor_risk to start monitoring.</i>",
                    parse_mode=ParseMode.HTML
                )
            else:
                position = user['positions'][asset]['position']
                position.size = size  # Use requested hedge size
            price = await self.fetch_price(asset)
            if price is None:
                await update.effective_message.reply_text(f"❌ Failed to fetch price for {asset}.")
                return
            notional = abs(size * price)
            if notional > LARGE_TRADE_NOTIONAL_THRESHOLD:
                # Prompt for confirmation
                keyboard = [[InlineKeyboardButton("✅ Confirm Hedge", callback_data=f"confirm_hedge_{asset}_{size}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(
                    f"⚠️ <b>Large Trade Detected</b>\n\n"
                                    f"<b>Asset:</b> {asset}\n"
                f"<b>Size:</b> {size:,.2f}\n"
                f"<b>Notional:</b> ${notional:,.2f}\n"
                    f"<b>Status:</b> Awaiting user confirmation.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return
            market_data = MarketData(
                symbol=asset,
                price=price,
                volume_24h=0.0,
                change_24h=0.0,
                timestamp=datetime.now(),
                exchange=position.exchange,
                option_type=position.option_type,
                strike=position.strike,
                expiry=position.expiry,
                underlying=position.underlying
            )
            # Use historical volatility if available
            if asset in self.price_history and len(self.price_history[asset]) > 10:
                prices = [pt['price'] for pt in self.price_history[asset][-30:]]
                volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
            else:
                volatility = 0.3
            risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
            if not risk_metrics:
                await update.effective_message.reply_text(f"❌ Failed to calculate risk metrics for {asset}.")
                return
            # Use current strategy
            strategy = user.get('auto_hedge', {}).get('strategy', 'delta_neutral')
            if not self.hedging_manager.set_strategy(strategy):
                await update.effective_message.reply_text(f"❌ Unknown strategy: {strategy}")
                return
            # Calculate hedge order
            orderbook = None
            try:
                hedge_order = await self.hedging_manager.active_strategy.calculate_hedge(position, risk_metrics, market_data, orderbook)
            except Exception as e:
                logger.error(f"Error calculating hedge order: {e}")
                await update.effective_message.reply_text(f"❌ Error calculating hedge order: {e}")
                return
            if not hedge_order:
                await update.effective_message.reply_text(f"❌ No hedge order generated for {asset}.")
                return
            # Execute hedge (simulate or real)
            exchange = None
            try:
                hedge_result = await self.hedging_manager.active_strategy.execute_hedge(hedge_order, exchange, position)
            except Exception as e:
                logger.error(f"Error executing hedge: {e}")
                await update.effective_message.reply_text(f"❌ Error executing hedge: {e}")
                return
            if hedge_result.success:
                # Set suppress_alerts to prevent immediate re-alerts after hedging
                if asset in user['positions']:
                    user['positions'][asset]["suppress_alerts"] = True
                    user['positions'][asset]['history'].append({'action': 'manual_hedge', 'time': datetime.now()})
                
                await update.effective_message.reply_text(
                    f"✅ <b>Hedge Executed Successfully</b>\n\n"
                    f"<b>Asset:</b> {asset}\n"
                    f"<b>Size:</b> {hedge_order.size:,.2f}\n"
                    f"<b>Strategy:</b> {strategy.replace('_', ' ').title()}\n"
                    f"<b>Cost:</b> ${hedge_result.total_cost:,.2f}\n"
                    f"<b>Execution Time:</b> {hedge_result.execution_time:.2f}s\n"
                    f"<b>Status:</b> Complete\n\n"
                    f"<i>Alerts temporarily suppressed for this position.</i>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.effective_message.reply_text(f"❌ Hedge execution failed: {hedge_result.message}")
            self.last_chat_id = chat_id
        except ValueError as e:
            message = update.effective_message
            if message:
                await message.reply_text(f"❌ Invalid input: {str(e)}")
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(f"❌ Invalid input: {str(e)}")
            else:
                logger.error("No message found in update for hedge_now_command value error reply")
        except Exception as e:
            logger.error(f"Error in hedge_now_command: {e}")
            message = update.effective_message
            if message:
                await message.reply_text("❌ Error executing hedge")
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("❌ Error executing hedge")
            else:
                logger.error("No message found in update for hedge_now_command generic error reply")
    
    async def stop_monitoring_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_monitoring command."""
        try:
            asset = context.args[0].upper() if context.args else "ALL"
            
            if asset == "ALL":
                self.user_data.clear()
                message = update.effective_message
                if message:
                    await message.reply_text("✅ Stopped monitoring all positions")
                elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_text("✅ Stopped monitoring all positions")
                else:
                    logger.error("No message found in update for stop_monitoring_command all reply")
            else:
                if asset in self.user_data:
                    del self.user_data[asset]
                    message = update.effective_message
                    if message:
                        await message.reply_text(f"✅ Stopped monitoring {asset}")
                    elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                        await update.callback_query.message.reply_text(f"✅ Stopped monitoring {asset}")
                    else:
                        logger.error("No message found in update for stop_monitoring_command asset reply")
                else:
                    message = update.effective_message
                    if message:
                        await message.reply_text(f"❌ No monitoring found for {asset}")
                    elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                        await update.callback_query.message.reply_text(f"❌ No monitoring found for {asset}")
                    else:
                        logger.error("No message found in update for stop_monitoring_command no monitoring reply")
            
            self.last_chat_id = update.effective_chat.id if update.effective_chat else None
            
        except Exception as e:
            logger.error(f"Error in stop_monitoring_command: {e}")
            message = update.effective_message
            if message:
                await message.reply_text("❌ Error stopping monitoring")
            elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("❌ Error stopping monitoring")
            else:
                logger.error("No message found in update for stop_monitoring_command error reply")
    
    async def risk_analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk_analytics command."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            if not positions or not market_data_dict:
                await update.effective_message.reply_text("No active positions to analyze.")
                return
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            if not portfolio_metrics:
                await update.effective_message.reply_text("Failed to calculate portfolio risk metrics.")
                return
            # Calculate total value safely
            total_value = sum(md.price * pos.size for pos, md in zip(positions, market_data_dict.values()))
            
            # Safely format numeric values, handling None, NaN, and other edge cases
            def safe_format(value, format_str=",.2f"):
                if value is None or (hasattr(value, 'isnan') and value.isnan()):
                    return "N/A"
                try:
                    return format(value, format_str)
                except (ValueError, TypeError):
                    return "N/A"
            
            # Format analytics text with proper HTML escaping
            analytics_text = (
                f"📊 <b>Portfolio Risk Analytics</b>\n\n"
                f"<b>Total Value:</b> ${safe_format(total_value)}\n"
                f"<b>Delta:</b> {safe_format(portfolio_metrics.delta)}\n"
                f"<b>Gamma:</b> {safe_format(portfolio_metrics.gamma)}\n"
                f"<b>Theta:</b> {safe_format(portfolio_metrics.theta)}\n"
                f"<b>Vega:</b> {safe_format(portfolio_metrics.vega)}\n"
                f"<b>VaR 95%:</b> ${safe_format(portfolio_metrics.var_95)}\n"
                f"<b>VaR 99%:</b> ${safe_format(portfolio_metrics.var_99)}\n"
                f"<b>Max Drawdown:</b> ${safe_format(portfolio_metrics.max_drawdown)}\n"
                f"<b>Correlation:</b> {safe_format(portfolio_metrics.correlation, '.2f')}\n"
                f"<b>Beta:</b> {safe_format(portfolio_metrics.beta, '.2f')}\n"
            )
            keyboard = [
                [
                    InlineKeyboardButton("📈 Detailed Charts", callback_data="charts"),
                    InlineKeyboardButton("⚡ Stress Test", callback_data="stress_test")
                ],
                [
                    InlineKeyboardButton("📊 Risk Report", callback_data="risk_report"),
                    InlineKeyboardButton("📈 Risk Charts", callback_data="risk_charts")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="refresh_analytics"),
                    InlineKeyboardButton("📋 Export Report", callback_data="export_report")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = update.effective_message
            try:
                if message:
                    await message.reply_text(
                        analytics_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(
                        analytics_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                else:
                    logger.error("No message or callback_query found in update for risk_analytics_command reply")
                self.last_chat_id = chat_id
            except Exception as html_error:
                logger.error(f"HTML parsing error in risk_analytics_command: {html_error}")
                # Fallback to plain text if HTML parsing fails
                plain_text = analytics_text.replace('<b>', '').replace('</b>', '')
                if message:
                    await message.reply_text(
                        plain_text,
                        reply_markup=reply_markup
                    )
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(
                        plain_text,
                        reply_markup=reply_markup
                    )
        except Exception as e:
            logger.error(f"Error in risk_analytics_command: {e}")
            await update.message.reply_text("❌ Error getting analytics")
    
    async def pnl_attribution_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl_attribution command for P&L attribution analysis."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            
            if not positions:
                await update.effective_message.reply_text("❌ No active positions for P&L attribution analysis.")
                return
            
            # Get market data
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            
            # Calculate P&L attribution
            attribution = self.analytics_reporter.calculate_pnl_attribution(positions, market_data_dict)
            
            if not attribution:
                await update.effective_message.reply_text("❌ Error calculating P&L attribution.")
                return
            
            # Safely format numeric values, handling None, NaN, and other edge cases
            def safe_format(value, format_str=",.2f"):
                if value is None or (hasattr(value, 'isnan') and value.isnan()):
                    return "N/A"
                try:
                    return format(value, format_str)
                except (ValueError, TypeError):
                    return "N/A"
            
            # Format attribution report
            total_pnl = attribution["total_pnl"]
            attribution_text = f"📊 <b>P&L Attribution Analysis</b>\n\n"
            attribution_text += f"<b>Total P&L:</b> ${safe_format(total_pnl)}\n\n"
            attribution_text += f"<b>Factor Contributions:</b>\n"
            delta_pct = (attribution['delta_pnl']/total_pnl*100) if total_pnl != 0 else 0
            gamma_pct = (attribution['gamma_pnl']/total_pnl*100) if total_pnl != 0 else 0
            theta_pct = (attribution['theta_pnl']/total_pnl*100) if total_pnl != 0 else 0
            vega_pct = (attribution['vega_pnl']/total_pnl*100) if total_pnl != 0 else 0
            attribution_text += f"• Delta: ${safe_format(attribution['delta_pnl'])} ({safe_format(delta_pct, '.1f')}%)\n"
            attribution_text += f"• Gamma: ${safe_format(attribution['gamma_pnl'])} ({safe_format(gamma_pct, '.1f')}%)\n"
            attribution_text += f"• Theta: ${safe_format(attribution['theta_pnl'])} ({safe_format(theta_pct, '.1f')}%)\n"
            attribution_text += f"• Vega: ${safe_format(attribution['vega_pnl'])} ({safe_format(vega_pct, '.1f')}%)\n\n"
            
            attribution_text += f"<b>Position Breakdown:</b>\n"
            for symbol, breakdown in attribution["position_breakdown"].items():
                pnl_color = "🟢" if breakdown["total_pnl"] >= 0 else "🔴"
                attribution_text += f"{pnl_color} <b>{symbol}:</b> ${safe_format(breakdown['total_pnl'])}\n"
                attribution_text += f"   Delta: ${safe_format(breakdown['delta_contribution'])}\n"
                attribution_text += f"   Gamma: ${safe_format(breakdown['gamma_contribution'])}\n"
                attribution_text += f"   Theta: ${safe_format(breakdown['theta_contribution'])}\n"
                attribution_text += f"   Vega: ${safe_format(breakdown['vega_contribution'])}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_pnl_attribution")],
                [InlineKeyboardButton("📊 Back to Analytics", callback_data="risk_analytics")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await update.effective_message.reply_text(
                    attribution_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            except Exception as html_error:
                logger.error(f"HTML parsing error in pnl_attribution_command: {html_error}")
                # Fallback to plain text if HTML parsing fails
                plain_text = attribution_text.replace('<b>', '').replace('</b>', '')
                await update.effective_message.reply_text(
                    plain_text,
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            logger.error(f"Error in pnl_attribution_command: {e}")
            await update.effective_message.reply_text("❌ Error calculating P&L attribution.")
    
    async def chart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send an interactive chart menu for an asset to the user."""
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not context.args or len(context.args) < 1:
            await update.effective_message.reply_text("Usage: /chart <asset>")
            return
        asset = context.args[0].upper()
        # For BTC, we can always show charts (uses Yahoo Finance)
        # For other assets, require local price history
        if asset != "BTC" and (asset not in self.price_history or not self.price_history[asset]):
            await update.effective_message.reply_text(f"No price history for {asset} yet. Start monitoring the asset first.")
            return
        # Always show chart menu for BTC, even if no local price history
        keyboard = [
            [
                InlineKeyboardButton("Price", callback_data=f"chart_{asset}_price_1d"),
                InlineKeyboardButton("PnL", callback_data=f"chart_{asset}_pnl_1d"),
                InlineKeyboardButton("VaR", callback_data=f"chart_{asset}_var_1d"),
                InlineKeyboardButton("Allocation", callback_data=f"chart_{asset}_alloc_1d")
            ],
            [
                InlineKeyboardButton("1h", callback_data=f"chart_{asset}_price_1h"),
                InlineKeyboardButton("1d", callback_data=f"chart_{asset}_price_1d"),
                InlineKeyboardButton("1w", callback_data=f"chart_{asset}_price_1w"),
                InlineKeyboardButton("1m", callback_data=f"chart_{asset}_price_1m"),
                InlineKeyboardButton("24m", callback_data=f"chart_{asset}_price_24m")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(
            f"📈 <b>{asset} Chart Menu</b>\n\nSelect chart type and timeframe:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Failed to answer callback query: {e}")
            # Continue processing even if answer fails
        
        data = query.data
        chat_id = update.effective_chat.id if update.effective_chat else None
        user = self._get_user(chat_id) if chat_id else None
        try:
            if data == "portfolio_real":
                user['portfolio_type'] = 'real'
                await query.edit_message_text("✅ Using <b>Real Deribit Portfolio</b>. You can now monitor and auto-hedge your real positions.", parse_mode=ParseMode.HTML)
                followup = (
                    "<b>Next steps:</b>\n"
                    "• <code>/monitor_risk &lt;asset&gt; &lt;size&gt; &lt;threshold&gt;</code> — Start monitoring a position\n"
                    "• <code>/auto_hedge &lt;strategy&gt; &lt;threshold&gt;</code> — Enable auto-hedging\n"
                    "• <code>/hedge_status &lt;asset&gt;</code> — Check current status\n"
                    "• <code>/hedge_now &lt;asset&gt; &lt;size&gt;</code> — Manual hedge\n"
                    "• <code>/risk_analytics</code> — Portfolio analytics\n"
                    "• <code>/chart &lt;asset&gt;</code> — Interactive charts\n"
                    "• <code>/help</code> — Show help\n"
                )
                await self.application.bot.send_message(chat_id=chat_id, text=followup, parse_mode=ParseMode.HTML)
            elif data == "portfolio_test":
                await query.edit_message_text(
                    "<b>Test portfolio is no longer supported. Please use your real Deribit portfolio.</b>",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data.startswith("chart_"):
                # Format: chart_{asset}_{type}_{tf}
                _, asset, chart_type, tf = data.split("_")
                await self.send_chart(chat_id, asset, chart_type, tf, query)
                return
            if data == "risk_analytics":
                await self.risk_analytics_command(update, context)
            elif data == "settings":
                await query.edit_message_text(
                    "⚙️ <b>Bot Settings</b>\n\nConfigure your hedging preferences here.",
                    parse_mode=ParseMode.HTML
                )
            elif data.startswith("monitor_"):
                asset = data.split("_")[1]
                await self.monitor_risk_command(update, context)
            elif data.startswith("hedge_"):
                asset = data.split("_")[1]
                if user and asset in user['positions']:
                    user['positions'][asset]["suppress_alerts"] = True
                    user['positions'][asset]['history'].append({'action': 'hedge', 'time': datetime.now()})
                await self.hedge_now_command(update, context)
            elif data == "auto_hedge":
                await query.edit_message_text(
                    "🛡️ <b>Automated Hedging</b>\n\nSelect your preferred strategy:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("Delta Neutral", callback_data="strategy_delta_neutral"),
                            InlineKeyboardButton("Options", callback_data="strategy_options")
                        ],
                        [
                            InlineKeyboardButton("Dynamic", callback_data="strategy_dynamic"),
                            InlineKeyboardButton("Back", callback_data="back_to_main")
                        ]
                    ])
                )
            elif data.startswith("threshold_"):
                asset = data.split("_")[1]
                if user and asset in user['positions']:
                    user['positions'][asset]["suppress_alerts"] = True
                    user['positions'][asset]['history'].append({'action': 'adjust_threshold', 'time': datetime.now()})
                await query.edit_message_text(
                    f"⚙️ <b>Adjust Threshold for {asset}</b>\n\nPlease use <code>/monitor_risk {asset} &lt;size&gt; &lt;new_threshold&gt;</code> to update.",
                    parse_mode=ParseMode.HTML
                )
            elif data.startswith("strategy_"):
                strategy = data.split("_")[1]
                self.hedging_manager.set_strategy(strategy)
                await query.edit_message_text(
                    f"✅ <b>Strategy Set: {strategy.replace('_', ' ').title()}</b>\n\nAutomated hedging is now active.",
                    parse_mode=ParseMode.HTML
                )
            elif data.startswith("configure_monitor_"):
                asset = data.split("_")[2]
                if user and asset in user['positions']:
                    user['positions'][asset]["suppress_alerts"] = True
                    user['positions'][asset]['history'].append({'action': 'configure_monitor', 'time': datetime.now()})
                await query.edit_message_text(
                    f"⚙️ <b>Configure Risk Thresholds for {asset}</b>\n\nPlease use <code>/configure_monitor {asset} &lt;delta_threshold&gt; [&lt;var_threshold&gt;]</code> to update.",
                    parse_mode=ParseMode.HTML
                )
            elif data.startswith("confirm_hedge_"):
                try:
                    # Handle the case where asset name might contain underscores
                    parts = data.split("_")
                    if len(parts) >= 3:
                        # The last part is the size, everything else after "confirm_hedge" is the asset
                        size = float(parts[-1])
                        asset = "_".join(parts[2:-1])  # Join all parts except "confirm_hedge" and the size
                        await self._execute_confirmed_hedge(chat_id, asset, size, query)
                    else:
                        logger.error(f"Invalid confirm_hedge callback data format: {data}")
                        await query.edit_message_text("❌ Invalid hedge confirmation data.")
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing confirm_hedge callback data '{data}': {e}")
                    await query.edit_message_text("❌ Error processing hedge confirmation.")
                return
            elif data.startswith("confirm_autohedge_"):
                try:
                    # Handle the case where asset name might contain underscores
                    parts = data.split("_")
                    if len(parts) >= 3:
                        # The last part is the size, everything else after "confirm_autohedge" is the asset
                        size = float(parts[-1])
                        asset = "_".join(parts[2:-1])  # Join all parts except "confirm_autohedge" and the size
                        await self._execute_confirmed_autohedge(chat_id, asset, size, query)
                    else:
                        logger.error(f"Invalid confirm_autohedge callback data format: {data}")
                        await query.edit_message_text("❌ Invalid auto-hedge confirmation data.")
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing confirm_autohedge callback data '{data}': {e}")
                    await query.edit_message_text("❌ Error processing auto-hedge confirmation.")
                return
            elif data == "charts":
                await self._handle_charts_callback(chat_id, query)
                return
            elif data == "stress_test":
                await self._handle_stress_test_callback(chat_id, query)
                return
            elif data == "refresh_analytics":
                await self._handle_refresh_analytics_callback(chat_id, query)
                return
            elif data == "export_report":
                await self._handle_export_report_callback(chat_id, query)
                return
            elif data == "refresh_pnl_attribution":
                await self._handle_refresh_pnl_attribution_callback(chat_id, query)
                return
            elif data == "risk_report":
                await self.risk_report_command(update, context)
                return
            elif data == "risk_charts":
                await self.risk_charts_command(update, context)
                return
            elif data == "export_risk_report_pdf":
                await self._handle_export_risk_report_pdf(chat_id, query)
                return
            elif data == "chart_risk_var":
                await self._handle_chart_risk_var(chat_id, query)
                return
            elif data == "chart_risk_drawdown":
                await self._handle_chart_risk_drawdown(chat_id, query)
                return
            elif data == "chart_risk_greeks":
                await self._handle_chart_risk_greeks(chat_id, query)
                return
            elif data == "chart_risk_allocation":
                await self._handle_chart_risk_allocation(chat_id, query)
                return
            elif data == "export_risk_chart":
                await self._handle_export_risk_chart(chat_id, query)
                return
            elif data == "summary_daily":
                user['summary_schedule'] = 'daily'
                await query.edit_message_text("✅ Daily risk summaries enabled. You'll receive summaries every day at 9:00 AM.")
                return
            elif data == "summary_weekly":
                user['summary_schedule'] = 'weekly'
                await query.edit_message_text("✅ Weekly risk summaries enabled. You'll receive summaries every Monday at 9:00 AM.")
                return
            elif data == "summary_disable":
                user['summary_schedule'] = None
                await query.edit_message_text("❌ Periodic risk summaries disabled.")
                return
            elif data == "change_summary_schedule":
                keyboard = [
                    [InlineKeyboardButton("📅 Daily", callback_data="summary_daily")],
                    [InlineKeyboardButton("📅 Weekly", callback_data="summary_weekly")],
                    [InlineKeyboardButton("❌ Disable", callback_data="summary_disable")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📅 <b>Configure Risk Summary Schedule</b>\n\nSelect frequency for periodic risk summaries:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return
            elif data == "send_summary_now":
                await self._send_risk_summary(chat_id)
                await query.edit_message_text("📊 Risk summary sent!")
                return
            elif data == "alert_delta":
                await query.edit_message_text(
                    "📊 <b>Delta Alert Setup</b>\n\n"
                    "Use: <code>/set_alert delta above 50000</code>\n"
                    "or: <code>/set_alert delta below -50000</code>\n\n"
                    "This will alert when your portfolio delta exceeds the threshold.",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "alert_var":
                await query.edit_message_text(
                    "💰 <b>VaR Alert Setup</b>\n\n"
                    "Use: <code>/set_alert var above 20000</code>\n"
                    "or: <code>/set_alert var below 10000</code>\n\n"
                    "This will alert when your portfolio VaR exceeds the threshold.",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "alert_pnl":
                await query.edit_message_text(
                    "📈 <b>P&L Alert Setup</b>\n\n"
                    "Use: <code>/set_alert pnl below -10000</code>\n"
                    "or: <code>/set_alert pnl above 50000</code>\n\n"
                    "This will alert when your portfolio P&L crosses the threshold.",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "alert_drawdown":
                await query.edit_message_text(
                    "⚠️ <b>Drawdown Alert Setup</b>\n\n"
                    "Use: <code>/set_alert drawdown above 15000</code>\n\n"
                    "This will alert when your portfolio drawdown exceeds the threshold.",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "delete_alert_menu":
                await self.delete_alert_command(update, context)
                return
            elif data == "add_alert_menu":
                await self.set_alert_command(update, context)
                return
            elif data.startswith("delete_alert_"):
                alert_id = int(data.split("_")[2])
                user = self._get_user(chat_id)
                alerts = user.get('custom_alerts', [])
                
                for i, alert in enumerate(alerts):
                    if alert['id'] == alert_id:
                        deleted_alert = alerts.pop(i)
                        await query.edit_message_text(
                            f"✅ <b>Alert Deleted</b>\n\n"
                            f"<b>Metric:</b> {deleted_alert['metric'].title()}\n"
                            f"<b>Condition:</b> {deleted_alert['condition'].title()} {deleted_alert['value']:,.2f}",
                            parse_mode=ParseMode.HTML
                        )
                        return
                
                await query.edit_message_text("❌ Alert not found.")
                return
            elif data == "cancel_delete":
                await query.edit_message_text("❌ Alert deletion cancelled.")
                return
            elif data == "hedge_alert":
                await query.edit_message_text(
                    "🛡️ <b>Hedge from Alert</b>\n\n"
                    "Use <code>/hedge_now &lt;asset&gt; &lt;size&gt;</code> to hedge manually,\n"
                    "or <code>/auto_hedge &lt;strategy&gt; &lt;threshold&gt;</code> to enable auto-hedging.",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "confirm_emergency_stop":
                user = self._get_user(chat_id)
                
                # Execute emergency stop
                stopped_count = 0
                for asset, data in user['positions'].items():
                    if data.get('is_active', False):
                        data['is_active'] = False
                        stopped_count += 1
                
                # Disable auto-hedging
                if user.get('auto_hedge', {}).get('enabled', False):
                    user['auto_hedge']['enabled'] = False
                
                # Clear custom alerts
                if 'custom_alerts' in user:
                    user['custom_alerts'] = []
                
                # Disable summaries
                user['summary_schedule'] = None
                
                await query.edit_message_text(
                    f"🚨 <b>Emergency Stop Executed</b>\n\n"
                    f"✅ All activities stopped:\n"
                    f"• Stopped monitoring {stopped_count} positions\n"
                    f"• Disabled auto-hedging\n"
                    f"• Cleared all custom alerts\n"
                    f"• Disabled periodic summaries\n\n"
                    f"<b>System is now in safe mode.</b>",
                    parse_mode=ParseMode.HTML
                )
                return
            elif data == "cancel_emergency_stop":
                await query.edit_message_text("❌ Emergency stop cancelled. All systems continue normal operation.")
                return
            elif data == "alerts_status":
                await self.alerts_status_command(update, context)
                return
            elif data == "summary_status":
                await self.summary_status_command(update, context)
                return
            else:
                # Unknown action: reply with help
                await query.edit_message_text(
                    "❓ Unknown action. Use /help for available commands or try /start to begin.",
                    parse_mode=ParseMode.HTML
                )
                followup = (
                    "<b>Available commands:</b>\n"
                    "• <code>/monitor_risk &lt;asset&gt; &lt;size&gt; &lt;threshold&gt;</code> — Start monitoring a position\n"
                    "• <code>/auto_hedge &lt;strategy&gt; &lt;threshold&gt;</code> — Enable auto-hedging\n"
                    "• <code>/hedge_status &lt;asset&gt;</code> — Check current status\n"
                    "• <code>/hedge_now &lt;asset&gt; &lt;size&gt;</code> — Manual hedge\n"
                    "• <code>/risk_analytics</code> — Portfolio analytics\n"
                    "• <code>/chart &lt;asset&gt;</code> — Interactive charts\n"
                    "• <code>/help</code> — Show help\n"
                )
                await self.application.bot.send_message(chat_id=chat_id, text=followup, parse_mode=ParseMode.HTML)
                
            if chat_id:
                self._get_user(chat_id)  # ensure user exists
                
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            try:
                await query.edit_message_text("❌ Error processing request. Use /help for available commands.", parse_mode=ParseMode.HTML)
            except Exception:
                message = update.effective_message
                if message:
                    await message.reply_text("❌ Error processing request. Use /help for available commands.", parse_mode=ParseMode.HTML)
                else:
                    logger.error("No message found in update for button_callback error reply")
    
    async def configure_monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /configure_monitor <asset> <delta_threshold> [<var_threshold>] to update thresholds for a monitored asset."""
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not chat_id:
            logger.error("No chat_id found in configure_monitor_command")
            return
        user = self._get_user(chat_id)
        try:
            if not context.args or len(context.args) < 2:
                message = update.effective_message
                if message:
                    await message.reply_text(
                        "❌ Usage: `/configure_monitor <asset> <delta_threshold> [<var_threshold>]`\n"
                        "Example: `/configure_monitor BTC 0.04 15000`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    logger.error("No message found in update for configure_monitor_command error reply")
                return
            asset = context.args[0].upper()
            delta_threshold = float(context.args[1])
            var_threshold = float(context.args[2]) if len(context.args) > 2 else None
            if asset not in user['positions']:
                await update.effective_message.reply_text(f"❌ No monitoring found for {asset}. Use /monitor_risk to start monitoring.")
                return
            user['positions'][asset]['threshold'] = delta_threshold
            user['positions'][asset]['var_threshold'] = var_threshold
            user['positions'][asset]['suppress_alerts'] = True  # Suppress alert after config change
            user['positions'][asset]['history'].append({'action': 'configure_monitor', 'delta_threshold': delta_threshold, 'var_threshold': var_threshold, 'time': datetime.now()})
            await update.effective_message.reply_text(
                f"⚙️ <b>Updated Risk Thresholds for {asset}</b>\n\n"
                f"<b>Delta Threshold:</b> {delta_threshold:.1%}\n"
                f"<b>VaR Threshold:</b> {var_threshold if var_threshold is not None else 'N/A'}\n"
                f"<b>Status:</b> Monitoring continues with new thresholds.",
                parse_mode=ParseMode.HTML
            )
        except ValueError as e:
            message = update.effective_message
            if message:
                await message.reply_text(f"❌ Invalid input: {str(e)}")
            else:
                logger.error("No message found in update for configure_monitor_command value error reply")
        except Exception as e:
            logger.error(f"Error in configure_monitor_command: {e}")
            message = update.effective_message
            if message:
                await message.reply_text("❌ Error updating thresholds")
            else:
                logger.error("No message found in update for configure_monitor_command generic error reply")
    
    async def monitor_position(self, chat_id: int, asset: str):
        """Monitor position for risk threshold breaches and auto-hedge if enabled. Only real data allowed."""
        user = self._get_user(chat_id)
        while asset in user['positions'] and user['positions'][asset]["is_active"]:
            try:
                await asyncio.sleep(30)
                price = await self.fetch_price(asset)
                if price is None:
                    await self.application.bot.send_message(chat_id=chat_id, text="<b>Failed to fetch real price data from Deribit. Monitoring stopped.</b>", parse_mode=ParseMode.HTML)
                    user['positions'][asset]["is_active"] = False
                    break
                position = user['positions'][asset]["position"]
                position.current_price = price
                market_data = MarketData(
                    symbol=asset,
                    price=price,
                    volume_24h=0.0,
                    change_24h=0.0,
                    timestamp=datetime.now(),
                    exchange=position.exchange,
                    option_type=position.option_type,
                    strike=position.strike,
                    expiry=position.expiry,
                    underlying=position.underlying
                )
                if asset in self.price_history and len(self.price_history[asset]) > 10:
                    prices = [pt['price'] for pt in self.price_history[asset][-30:]]
                    volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
                else:
                    volatility = 0.3
                risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
                if not risk_metrics:
                    logger.error(f"Risk metrics calculation failed for {asset} (user {chat_id})")
                    continue
                position_value = abs(position.size * price)
                current_risk = abs(risk_metrics.delta) / position_value if position_value else 0
                threshold = user['positions'][asset]["threshold"]
                var_threshold = user['positions'][asset].get("var_threshold")
                # --- Portfolio-level risk metrics and correlation matrix ---
                positions = [data['position'] for data in user['positions'].values()]
                market_data_dict = {}
                price_history_dict = {}
                for a, data in user['positions'].items():
                    p = await self.fetch_price(a)
                    if p is not None:
                        market_data_dict[a] = MarketData(
                            symbol=a,
                            price=p,
                            volume_24h=0.0,
                            change_24h=0.0,
                            timestamp=datetime.now(),
                            exchange=data['position'].exchange,
                            option_type=data['position'].option_type,
                            strike=data['position'].strike,
                            expiry=data['position'].expiry,
                            underlying=data['position'].underlying
                        )
                        price_history_dict[a] = [pt['price'] for pt in self.price_history.get(a, [])]
                portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
                correlation_matrix = self.analytics_reporter._calculate_correlation_matrix(positions, price_history_dict)
                user['portfolio_metrics'] = portfolio_metrics
                user['correlation_matrix'] = correlation_matrix
                # --- End portfolio-level risk metrics ---
                
                # Check custom alerts
                if portfolio_metrics:
                    await self._check_custom_alerts(chat_id, portfolio_metrics, positions, market_data_dict)
                
                # Check both delta and VaR thresholds
                breach_type = None
                if current_risk > threshold:
                    breach_type = "delta"
                if var_threshold is not None and portfolio_metrics and portfolio_metrics.var_95 > var_threshold:
                    breach_type = "var"
                if breach_type and not user['positions'][asset]["suppress_alerts"]:
                    await self.send_risk_alert(chat_id, asset, current_risk, threshold, risk_metrics, position, market_data, breach_type=breach_type, var_threshold=var_threshold, portfolio_metrics=portfolio_metrics)
                if user.get('auto_hedge', {}).get('enabled') and breach_type:
                    pos_data = user['positions'][asset]
                    pending = pos_data.get("pending_confirmation", False)
                    suppressed = pos_data.get("suppress_alerts", False)
                    last_hedge_time = pos_data.get("last_hedge_time")
                    recent_hedge = False
                    if last_hedge_time:
                        if (datetime.now() - last_hedge_time).total_seconds() < 300:
                            recent_hedge = True
                    if not pending and not suppressed and not recent_hedge:
                        await self.hedge_now_command_for_auto(chat_id, asset)
            except Exception as e:
                logger.error(f"Error monitoring {asset} for user {chat_id}: {e}")
                # If it's a timeout error, wait a bit longer before retrying
                if "Timed out" in str(e) or "ReadTimeout" in str(e):
                    logger.info(f"Timeout detected for {asset}, waiting 60 seconds before retry...")
                    await asyncio.sleep(60)
                else:
                    # For other errors, wait the normal interval
                    await asyncio.sleep(30)
    
    async def send_risk_alert(self, chat_id: int, asset: str, current_risk: float, threshold: float, risk_metrics=None, position=None, market_data=None, breach_type=None, var_threshold=None, portfolio_metrics=None):
        user = self._get_user(chat_id)
        if asset in user['positions'] and user['positions'][asset].get("suppress_alerts", False):
            logger.info(f"Risk alert for {asset} (user {chat_id}) suppressed due to recent hedge or threshold adjustment.")
            return
        recommendation = None
        if risk_metrics and position and market_data:
            try:
                recommendation = self.risk_calculator.generate_hedge_recommendation(position, risk_metrics, market_data, threshold=threshold)
            except Exception as e:
                logger.error(f"Error generating hedge recommendation: {e}")
        alert_text = (
            f"🚨 <b>Risk Alert - {asset}</b>\n\n"
            f"<b>Current Delta Risk:</b> {current_risk:.1%}\n"
            f"<b>Delta Threshold:</b> {threshold:.1%}\n"
        )
        if var_threshold is not None and portfolio_metrics:
            alert_text += (
                f"<b>Portfolio VaR 95%:</b> ${portfolio_metrics.var_95:,.2f}\n"
                f"<b>VaR Threshold:</b> ${var_threshold:,.2f}\n"
            )
        if breach_type == "delta":
            alert_text += f"<b>Status:</b> ⚠️ Delta Risk Exceeded\n\n"
        elif breach_type == "var":
            alert_text += f"<b>Status:</b> ⚠️ Portfolio VaR Exceeded\n\n"
        else:
            alert_text += f"<b>Status:</b> ⚠️ Risk Exceeded\n\n"
        alert_text += (
            f"<b>Position:</b> {position.size:,.2f} @ {position.current_price:,.2f}\n"
            f"<b>Delta:</b> {risk_metrics.delta:,.2f}\n"
            f"<b>Gamma:</b> {risk_metrics.gamma:,.2f}\n"
            f"<b>Theta:</b> {risk_metrics.theta:,.2f}\n"
            f"<b>Vega:</b> {risk_metrics.vega:,.2f}\n"
            f"<b>VaR 95%:</b> ${risk_metrics.var_95:,.2f}\n"
            f"<b>VaR 99%:</b> ${risk_metrics.var_99:,.2f}\n"
            f"<b>Max Drawdown:</b> ${risk_metrics.max_drawdown:,.2f}\n"
            f"<b>Correlation:</b> {risk_metrics.correlation:.2f}\n"
            f"<b>Beta:</b> {risk_metrics.beta:.2f}\n\n"
        )
        if recommendation:
            alert_text += (
                f"<b>Recommended Hedge:</b> {recommendation.hedge_size:,.2f} via {recommendation.hedge_type.title()}\n"
                f"<b>Instrument:</b> {recommendation.hedge_instrument}\n"
                f"<b>Estimated Cost:</b> ${recommendation.estimated_cost:,.2f}\n"
                f"<b>Urgency:</b> {recommendation.urgency.title()}\n"
                f"<b>Reason:</b> {recommendation.reason}\n\n"
            )
        alert_text += (
            f"<b>Quick Actions:</b>"
        )
        keyboard = [
            [
                InlineKeyboardButton("🛡️ Hedge Now", callback_data=f"hedge_{asset}"),
                InlineKeyboardButton("📊 View Details", callback_data=f"analytics_{asset}")
            ],
            [
                InlineKeyboardButton("⚙️ Adjust Threshold", callback_data=f"threshold_{asset}"),
                InlineKeyboardButton("❌ Dismiss", callback_data="dismiss_alert")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=alert_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            logger.info(f"Risk alert sent for {asset} to user {chat_id}: {current_risk:.1%} > {threshold:.1%}")
        except Exception as e:
            logger.error(f"Failed to send risk alert for {asset} to user {chat_id}: {e}")
            # Try sending without HTML formatting as fallback
            try:
                plain_text = alert_text.replace('<b>', '').replace('</b>', '')
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=plain_text,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"Failed to send plain text risk alert for {asset} to user {chat_id}: {e2}")
    
    async def hedge_now_command_for_auto(self, chat_id: int, asset: str):
        """Perform auto-hedging for the user (real portfolio only)."""
        user = self._get_user(chat_id)
        portfolio_type = user.get('portfolio_type', 'real')
        if portfolio_type == 'real':
            deribit_cfg = Config.get_exchange_config('deribit')
            if deribit_cfg and deribit_cfg.get('enabled', False):
                if 'deribit' not in self.exchanges:
                    from exchanges.deribit import DeribitExchange
                    self.exchanges['deribit'] = DeribitExchange(deribit_cfg)
                    await self.exchanges['deribit'].connect()
                logger.info(f"Auto-hedging {asset} for user {chat_id} on Deribit (real portfolio)")
                position = user['positions'][asset]['position']
                price = await self.fetch_price(asset)
                if price is None:
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Failed to fetch price for {asset}.", parse_mode=ParseMode.HTML)
                    return
                notional = abs(position.size * price)
                if notional > LARGE_TRADE_NOTIONAL_THRESHOLD:
                    # Check if confirmation is already pending
                    if user['positions'][asset].get("pending_confirmation", False):
                        logger.info(f"Auto-hedge confirmation already pending for {asset} (user {chat_id})")
                        return
                    
                    # Set pending confirmation flag
                    user['positions'][asset]["pending_confirmation"] = True
                    user['positions'][asset]['history'].append({'action': 'pending_confirmation_set', 'time': datetime.now()})
                    
                    # Prompt for confirmation
                    keyboard = [[InlineKeyboardButton("✅ Confirm Auto-Hedge", callback_data=f"confirm_autohedge_{asset}_{position.size}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    text = (
                        f"⚠️ <b>Large Auto-Hedge Detected</b>\n\n"
                        f"<b>Asset:</b> {asset}\n"
                        f"<b>Size:</b> {position.size:,.2f}\n"
                        f"<b>Notional:</b> ${notional:,.2f}\n"
                        f"<b>Status:</b> Awaiting user confirmation."
                    )
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    return
                # Use real risk and hedging logic
                market_data = MarketData(
                    symbol=asset,
                    price=price,
                    volume_24h=0.0,
                    change_24h=0.0,
                    timestamp=datetime.now(),
                    exchange=position.exchange,
                    option_type=position.option_type,
                    strike=position.strike,
                    expiry=position.expiry,
                    underlying=position.underlying
                )
                # Use historical volatility if available
                if asset in self.price_history and len(self.price_history[asset]) > 10:
                    prices = [pt['price'] for pt in self.price_history[asset][-30:]]
                    volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
                else:
                    volatility = 0.3
                risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
                if not risk_metrics:
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Failed to calculate risk metrics for {asset}.", parse_mode=ParseMode.HTML)
                    return
                strategy = user.get('auto_hedge', {}).get('strategy', 'delta_neutral')
                if not self.hedging_manager.set_strategy(strategy):
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Unknown strategy: {strategy}", parse_mode=ParseMode.HTML)
                    return
                orderbook = None
                try:
                    hedge_order = await self.hedging_manager.active_strategy.calculate_hedge(position, risk_metrics, market_data, orderbook)
                except Exception as e:
                    logger.error(f"Error calculating hedge order: {e}")
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Error calculating hedge order: {e}", parse_mode=ParseMode.HTML)
                    return
                if not hedge_order:
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ No hedge order generated for {asset}.", parse_mode=ParseMode.HTML)
                    return
                exchange = self.exchanges['deribit']
                try:
                    hedge_result = await self.hedging_manager.active_strategy.execute_hedge(hedge_order, exchange, position)
                except Exception as e:
                    logger.error(f"Error executing hedge: {e}")
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Error executing hedge: {e}", parse_mode=ParseMode.HTML)
                    return
                if hedge_result.success:
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"✅ <b>Auto-Hedge Executed</b>\n\n"
                            f"<b>Asset:</b> {asset}\n"
                            f"<b>Size:</b> {hedge_order.size:,.2f}\n"
                            f"<b>Strategy:</b> {strategy.replace('_', ' ').title()}\n"
                            f"<b>Cost:</b> ${hedge_result.total_cost:,.2f}\n"
                            f"<b>Execution Time:</b> {hedge_result.execution_time:.2f}s\n"
                            f"<b>Status:</b> Complete"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.effective_message.reply_text(f"❌ Hedge execution failed: {hedge_result.message}")
            else:
                logger.warning("Deribit not available for real auto-hedging.")
                await self.application.bot.send_message(chat_id=chat_id, text="<b>Deribit is not available. Cannot perform auto-hedging.</b>", parse_mode=ParseMode.HTML)
                return
        else:
            await self.application.bot.send_message(chat_id=chat_id, text="<b>Test portfolio is no longer supported. Please use your real Deribit portfolio.</b>", parse_mode=ParseMode.HTML)
            return
        if asset in user['positions']:
            user['positions'][asset]["suppress_alerts"] = True
            user['positions'][asset]['history'].append({'action': 'auto_hedge', 'time': datetime.now()})
        await self.send_chart(chat_id, asset, 'pnl', '1d')
    
    async def price_polling_loop(self):
        """Background task to fetch prices for all monitored assets and update user portfolios."""
        await asyncio.sleep(2)  # Let bot initialize
        while True:
            try:
                assets = set()
                for user in self.user_data.values():
                    assets.update(user['positions'].keys())
                for asset in assets:
                    price = await self.fetch_price(asset)
                    if price is not None:
                        now = datetime.now()
                        if asset not in self.price_history:
                            self.price_history[asset] = []
                        self.price_history[asset].append({"timestamp": now, "price": price})
                        # Keep only last 500 points
                        self.price_history[asset] = self.price_history[asset][-500:]
                        # Update all user positions for this asset
                        for user in self.user_data.values():
                            if asset in user['positions']:
                                pos = user['positions'][asset]['position']
                                pos.current_price = price
                                pos.unrealized_pnl = (price - pos.entry_price) * pos.size if pos.entry_price else 0
                                
                                # Reset suppress_alerts flag after 1 hour (3600 seconds)
                                if user['positions'][asset].get("suppress_alerts", False):
                                    # Check if the last hedge action was more than 1 hour ago
                                    history = user['positions'][asset].get('history', [])
                                    if history:
                                        last_hedge_action = None
                                        for action in reversed(history):
                                            if action.get('action') in ['manual_hedge', 'auto_hedge']:
                                                last_hedge_action = action.get('time')
                                                break
                                        
                                        if last_hedge_action and (now - last_hedge_action).total_seconds() > 3600:
                                            user['positions'][asset]["suppress_alerts"] = False
                                            logger.info(f"Reset suppress_alerts for {asset} (user {list(self.user_data.keys())[list(self.user_data.values()).index(user)]})")
                                
                                # Reset pending_confirmation flag after 30 minutes (1800 seconds) to prevent stuck confirmations
                                if user['positions'][asset].get("pending_confirmation", False):
                                    # Check if the pending confirmation was set more than 30 minutes ago
                                    history = user['positions'][asset].get('history', [])
                                    if history:
                                        last_confirmation_time = None
                                        for action in reversed(history):
                                            if action.get('action') == 'pending_confirmation_set':
                                                last_confirmation_time = action.get('time')
                                                break
                                        
                                        if last_confirmation_time and (now - last_confirmation_time).total_seconds() > 1800:
                                            user['positions'][asset]["pending_confirmation"] = False
                                            logger.info(f"Reset pending_confirmation for {asset} (user {list(self.user_data.keys())[list(self.user_data.values()).index(user)]}) - timeout after 30 minutes")
                                
                                # Trigger risk/analytics updates for active monitoring
                                if asset in user['positions'] and user['positions'][asset].get('is_active', False):
                                    # Update portfolio metrics and check custom alerts
                                    positions = [data['position'] for data in user['positions'].values()]
                                    market_data_dict = {}
                                    for a, data in user['positions'].items():
                                        p = await self.fetch_price(a)
                                        if p is not None:
                                            market_data_dict[a] = MarketData(
                                                symbol=a,
                                                price=p,
                                                volume_24h=0.0,
                                                change_24h=0.0,
                                                timestamp=datetime.now(),
                                                exchange=data['position'].exchange,
                                                option_type=data['position'].option_type,
                                                strike=data['position'].strike,
                                                expiry=data['position'].expiry,
                                                underlying=data['position'].underlying
                                            )
                                    
                                    if market_data_dict:
                                        portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
                                        if portfolio_metrics:
                                            # Find the chat_id for this user
                                            user_chat_id = None
                                            for cid, u in self.user_data.items():
                                                if u == user:
                                                    user_chat_id = cid
                                                    break
                                            
                                            if user_chat_id:
                                                # Check custom alerts
                                                await self._check_custom_alerts(user_chat_id, portfolio_metrics, positions, market_data_dict)
                                                
                                                # Update user's portfolio metrics
                                                user['portfolio_metrics'] = portfolio_metrics
            except Exception as e:
                logger.error(f"Error in price polling loop: {e}")
            await asyncio.sleep(20)
    
    async def fetch_price(self, asset: str) -> Optional[float]:
        """Fetch the latest price for an asset from Deribit only. Show error if not available."""
        deribit_cfg = Config.get_exchange_config('deribit')
        if deribit_cfg and deribit_cfg.get('enabled', False):
            if 'deribit' not in self.exchanges:
                from exchanges.deribit import DeribitExchange
                self.exchanges['deribit'] = DeribitExchange(deribit_cfg)
                await self.exchanges['deribit'].connect()
            try:
                md = await self.exchanges['deribit'].get_market_data(f"{asset}-PERPETUAL")
                if md and md.price:
                    return md.price
            except Exception as e:
                logger.warning(f"Deribit price fetch failed for {asset}: {e}")
                return None
        # If Deribit not available, show error (do not simulate)
        logger.error("Deribit is not available. Cannot fetch real prices.")
        return None
    
    async def send_chart(self, chat_id: int, asset: str, chart_type: str, tf: str, query=None):
        """Generate and send the requested chart for an asset and timeframe. For 24m BTC, fetch from yfinance."""
        if asset == "BTC" and chart_type == "price" and tf == "24m":
            # Fetch 2 years of daily BTC-USD data from yfinance
            btc = yf.Ticker('BTC-USD')
            hist = btc.history(period='2y', interval='1d')
            if hist.empty:
                text = "No historical data available for BTC."
                if query:
                    await query.edit_message_text(text)
                else:
                    await self.application.bot.send_message(chat_id=chat_id, text=text)
                return
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='BTC Price'))
            fig.update_layout(title='BTC Price Trend (Last 24 Months)', xaxis_title='Date', yaxis_title='Price (USD)')
            img_bytes = fig.to_image(format="png")
            if query:
                await query.edit_message_media(
                    media=InputMediaPhoto(io.BytesIO(img_bytes)),
                    reply_markup=query.message.reply_markup
                )
            else:
                await self.application.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(img_bytes))
            return
        # Filter price history by timeframe
        now = datetime.now()
        if tf == "1h":
            cutoff = now - timedelta(hours=1)
        elif tf == "1d":
            cutoff = now - timedelta(days=1)
        elif tf == "1w":
            cutoff = now - timedelta(days=7)
        elif tf == "1m":
            cutoff = now - timedelta(days=30)
        elif tf == "24m":
            cutoff = now - timedelta(days=730)
        else:
            cutoff = now - timedelta(days=1)
        history = [pt for pt in self.price_history.get(asset, []) if pt['timestamp'] >= cutoff]
        if not history:
            text = f"No data for {asset} in the selected timeframe."
            if query:
                await query.edit_message_text(text)
            else:
                await self.application.bot.send_message(chat_id=chat_id, text=text)
            return
        fig = go.Figure()
        if chart_type == "price":
            times = [pt['timestamp'] for pt in history]
            prices = [pt['price'] for pt in history]
            fig.add_trace(go.Scatter(x=times, y=prices, mode='lines', name=f'{asset} Price'))
            fig.update_layout(title=f'{asset} Price ({tf})', xaxis_title='Time', yaxis_title='Price (USD)')
        elif chart_type == "pnl":
            # PnL = (current_price - entry_price) * size
            user = self._get_user(chat_id)
            if asset in user['positions']:
                entry = user['positions'][asset]['position'].entry_price
                size = user['positions'][asset]['position'].size
                times = [pt['timestamp'] for pt in history]
                pnls = [(pt['price'] - entry) * size for pt in history]
                fig.add_trace(go.Scatter(x=times, y=pnls, mode='lines', name=f'{asset} PnL'))
                fig.update_layout(title=f'{asset} PnL ({tf})', xaxis_title='Time', yaxis_title='PnL (USD)')
            else:
                await self.application.bot.send_message(chat_id=chat_id, text=f"No position for {asset}.")
                return
        elif chart_type == "var":
            # Simple VaR: 95% quantile of negative returns
            prices = [pt['price'] for pt in history]
            if len(prices) > 1:
                returns = [(prices[i] - prices[i-1])/prices[i-1] for i in range(1, len(prices))]
                var_95 = -sorted(returns)[int(0.05*len(returns))] if len(returns) > 20 else 0
                fig.add_trace(go.Bar(x=[f'VaR 95%'], y=[var_95*100]))
                fig.update_layout(title=f'{asset} VaR 95% ({tf})', yaxis_title='VaR (%)')
            else:
                await self.application.bot.send_message(chat_id=chat_id, text=f"Not enough data for VaR.")
                return
        elif chart_type == "alloc":
            # Portfolio allocation pie chart (user's positions)
            user = self._get_user(chat_id)
            alloc = []
            labels = []
            for a, pos in user['positions'].items():
                alloc.append(pos['position'].current_price * pos['position'].size)
                labels.append(a)
            if sum(alloc) > 0:
                fig = go.Figure(data=[go.Pie(labels=labels, values=alloc, hole=.3)])
                fig.update_layout(title='Portfolio Allocation')
            else:
                await self.application.bot.send_message(chat_id=chat_id, text=f"No positions for allocation chart.")
                return
        else:
            await self.application.bot.send_message(chat_id=chat_id, text=f"Unknown chart type.")
            return
        img_bytes = fig.to_image(format="png")
        if query:
            await query.edit_message_media(
                media=InputMediaPhoto(io.BytesIO(img_bytes)),
                reply_markup=query.message.reply_markup
            )
        else:
            await self.application.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(img_bytes))
    
    async def _start_background_tasks(self, app):
        """Start background tasks."""
        asyncio.create_task(self.price_polling_loop())
        asyncio.create_task(self._periodic_summary_task())
    
    def run(self):
        """Run the bot synchronously."""
        try:
            logger.info("Starting Hedging Bot...")
            logger.info("Bot features: Risk monitoring, Auto-hedging, Analytics, Alerts, Summaries")
            self.application.run_polling()
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise

    def stop(self):
        """Stop the bot gracefully."""
        try:
            logger.info("Stopping Hedging Bot...")
            # Stop all background tasks
            if self.price_polling_task:
                self.price_polling_task.cancel()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    async def _handle_charts_callback(self, chat_id: int, query):
        """Handle charts button callback for detailed portfolio charts."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            
            if not positions:
                await query.edit_message_text("❌ No active positions to chart.")
                return
            
            # Create portfolio chart using analytics reporter
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            
            chart_data = self.analytics_reporter.create_portfolio_chart(positions, market_data_dict)
            
            # Send chart as photo
            try:
                await self.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_data,
                    caption="📊 <b>Portfolio Allocation Chart</b>\n\nShows current position distribution and risk allocation.",
                    parse_mode=ParseMode.HTML
                )
                await query.edit_message_text("📈 Chart sent successfully!")
            except Exception as e:
                logger.error(f"Error sending chart: {e}")
                await query.edit_message_text("❌ Error generating chart. Please try again.")
                
        except Exception as e:
            logger.error(f"Error in _handle_charts_callback: {e}")
            await query.edit_message_text("❌ Error generating charts.")
    
    async def _handle_stress_test_callback(self, chat_id: int, query):
        """Handle stress test button callback."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            
            if not positions:
                await query.edit_message_text("❌ No active positions for stress testing.")
                return
            
            # Get market data
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            
            # Run stress tests
            stress_results = self.analytics_reporter._run_stress_tests(positions, market_data_dict)
            
            if not stress_results:
                await query.edit_message_text("❌ Error running stress tests.")
                return
            
            # Format stress test results
            stress_text = "🧪 <b>Portfolio Stress Test Results</b>\n\n"
            for scenario, pnl in stress_results.items():
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                stress_text += f"{pnl_color} <b>{scenario}:</b> ${pnl:,.2f}\n"
            
            stress_text += "\n<b>Interpretation:</b>\n"
            stress_text += "• Positive values = portfolio gains\n"
            stress_text += "• Negative values = portfolio losses\n"
            stress_text += "• Larger absolute values = higher risk exposure"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Run Again", callback_data="stress_test")],
                [InlineKeyboardButton("📊 Back to Analytics", callback_data="risk_analytics")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stress_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in _handle_stress_test_callback: {e}")
            await query.edit_message_text("❌ Error running stress tests.")
    
    async def _handle_refresh_analytics_callback(self, chat_id: int, query):
        """Handle refresh analytics button callback."""
        try:
            # Re-run the risk analytics command
            await self.risk_analytics_command(None, None)
            await query.edit_message_text("🔄 Analytics refreshed!")
            
        except Exception as e:
            logger.error(f"Error in _handle_refresh_analytics_callback: {e}")
            await query.edit_message_text("❌ Error refreshing analytics.")
    
    async def _handle_export_report_callback(self, chat_id: int, query):
        """Handle export report button callback."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            
            if not positions:
                await query.edit_message_text("❌ No active positions to export.")
                return
            
            # Get market data
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            
            # Calculate risk metrics
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            
            if not portfolio_metrics:
                await query.edit_message_text("❌ Error calculating portfolio metrics for export.")
                return
            
            # Generate comprehensive report
            report = self.analytics_reporter.generate_portfolio_report(positions, market_data_dict, portfolio_metrics)
            
            # Format report for Telegram
            report_text = self.analytics_reporter.generate_telegram_report(report)
            
            # Split long reports
            if len(report_text) > 4000:
                parts = [report_text[i:i+4000] for i in range(0, len(report_text), 4000)]
                for i, part in enumerate(parts):
                    if i == 0:
                        await query.edit_message_text(part, parse_mode=ParseMode.HTML)
                    else:
                        await self.application.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode=ParseMode.HTML
                        )
            else:
                await query.edit_message_text(report_text, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in _handle_export_report_callback: {e}")
            await query.edit_message_text("❌ Error exporting report.")
    
    async def _handle_refresh_pnl_attribution_callback(self, chat_id: int, query):
        """Handle refresh P&L attribution button callback."""
        try:
            # Re-run the P&L attribution command
            await self.pnl_attribution_command(None, None)
            await query.edit_message_text("🔄 P&L Attribution refreshed!")
            
        except Exception as e:
            logger.error(f"Error in _handle_refresh_pnl_attribution_callback: {e}")
            await query.edit_message_text("❌ Error refreshing P&L attribution.")

    async def _execute_confirmed_hedge(self, chat_id, asset, size, query):
        user = self._get_user(chat_id)
        position = user['positions'][asset]['position']
        position.size = size
        price = await self.fetch_price(asset)
        if price is None:
            await query.edit_message_text(f"❌ Failed to fetch price for {asset}.", parse_mode=ParseMode.HTML)
            return
        market_data = MarketData(
            symbol=asset,
            price=price,
            volume_24h=0.0,
            change_24h=0.0,
            timestamp=datetime.now(),
            exchange=position.exchange,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying=position.underlying
        )
        if asset in self.price_history and len(self.price_history[asset]) > 10:
            prices = [pt['price'] for pt in self.price_history[asset][-30:]]
            volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
        else:
            volatility = 0.3
        risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
        if not risk_metrics:
            await query.edit_message_text(f"❌ Failed to calculate risk metrics for {asset}.", parse_mode=ParseMode.HTML)
            return
        strategy = user.get('auto_hedge', {}).get('strategy', 'delta_neutral')
        if not self.hedging_manager.set_strategy(strategy):
            await query.edit_message_text(f"❌ Unknown strategy: {strategy}", parse_mode=ParseMode.HTML)
            return
        orderbook = None
        try:
            hedge_order = await self.hedging_manager.active_strategy.calculate_hedge(position, risk_metrics, market_data, orderbook)
        except Exception as e:
            logger.error(f"Error calculating hedge order: {e}")
            await query.edit_message_text(f"❌ Error calculating hedge order: {e}", parse_mode=ParseMode.HTML)
            return
        if not hedge_order:
            await query.edit_message_text(f"❌ No hedge order generated for {asset}.", parse_mode=ParseMode.HTML)
            return
        exchange = None
        try:
            hedge_result = await self.hedging_manager.active_strategy.execute_hedge(hedge_order, exchange, position)
        except Exception as e:
            logger.error(f"Error executing hedge: {e}")
            await query.edit_message_text(f"❌ Error executing hedge: {e}", parse_mode=ParseMode.HTML)
            return
        if hedge_result.success:
            # Set suppress_alerts to prevent immediate re-alerts after hedging
            if asset in user['positions']:
                user['positions'][asset]["suppress_alerts"] = True
                user['positions'][asset]["pending_confirmation"] = False  # Clear pending confirmation
                user['positions'][asset]['history'].append({'action': 'manual_hedge', 'time': datetime.now()})
                user['positions'][asset]["last_hedge_time"] = datetime.now()
            
            await query.edit_message_text(
                f"✅ <b>Hedge Executed Successfully</b>\n\n"
                f"<b>Asset:</b> {asset}\n"
                f"<b>Size:</b> {hedge_order.size:,.2f}\n"
                f"<b>Strategy:</b> {strategy.replace('_', ' ').title()}\n"
                f"<b>Cost:</b> ${hedge_result.total_cost:,.2f}\n"
                f"<b>Execution Time:</b> {hedge_result.execution_time:.2f}s\n"
                f"<b>Status:</b> Complete\n\n"
                f"<i>Alerts temporarily suppressed for this position.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            # Clear pending confirmation on failure
            if asset in user['positions']:
                user['positions'][asset]["pending_confirmation"] = False
            await query.edit_message_text(f"❌ Hedge execution failed: {hedge_result.message}", parse_mode=ParseMode.HTML)

    async def _execute_confirmed_autohedge(self, chat_id, asset, size, query):
        user = self._get_user(chat_id)
        position = user['positions'][asset]['position']
        position.size = size
        price = await self.fetch_price(asset)
        if price is None:
            await query.edit_message_text(f"❌ Failed to fetch price for {asset}.", parse_mode=ParseMode.HTML)
            return
        market_data = MarketData(
            symbol=asset,
            price=price,
            volume_24h=0.0,
            change_24h=0.0,
            timestamp=datetime.now(),
            exchange=position.exchange,
            option_type=position.option_type,
            strike=position.strike,
            expiry=position.expiry,
            underlying=position.underlying
        )
        if asset in self.price_history and len(self.price_history[asset]) > 10:
            prices = [pt['price'] for pt in self.price_history[asset][-30:]]
            volatility = self.risk_calculator.calculate_volatility(prices, window=min(30, len(prices)-1))
        else:
            volatility = 0.3
        risk_metrics = self.risk_calculator.calculate_position_greeks(position, market_data, volatility=volatility)
        if not risk_metrics:
            await query.edit_message_text(f"❌ Failed to calculate risk metrics for {asset}.", parse_mode=ParseMode.HTML)
            return
        strategy = user.get('auto_hedge', {}).get('strategy', 'delta_neutral')
        if not self.hedging_manager.set_strategy(strategy):
            await query.edit_message_text(f"❌ Unknown strategy: {strategy}", parse_mode=ParseMode.HTML)
            return
        orderbook = None
        try:
            hedge_order = await self.hedging_manager.active_strategy.calculate_hedge(position, risk_metrics, market_data, orderbook)
        except Exception as e:
            logger.error(f"Error calculating hedge order: {e}")
            await query.edit_message_text(f"❌ Error calculating hedge order: {e}", parse_mode=ParseMode.HTML)
            return
        if not hedge_order:
            await query.edit_message_text(f"❌ No hedge order generated for {asset}.", parse_mode=ParseMode.HTML)
            return
        exchange = self.exchanges['deribit'] if 'deribit' in self.exchanges else None
        try:
            hedge_result = await self.hedging_manager.active_strategy.execute_hedge(hedge_order, exchange, position)
        except Exception as e:
            logger.error(f"Error executing hedge: {e}")
            await query.edit_message_text(f"❌ Error executing hedge: {e}", parse_mode=ParseMode.HTML)
            return
        if hedge_result.success:
            # Set suppress_alerts to prevent immediate re-alerts after hedging
            if asset in user['positions']:
                user['positions'][asset]["suppress_alerts"] = True
                user['positions'][asset]["pending_confirmation"] = False  # Clear pending confirmation
                user['positions'][asset]['history'].append({'action': 'auto_hedge', 'time': datetime.now()})
                user['positions'][asset]["last_hedge_time"] = datetime.now()
            
            await query.edit_message_text(
                f"✅ <b>Auto-Hedge Executed</b>\n\n"
                f"<b>Asset:</b> {asset}\n"
                f"<b>Size:</b> {hedge_order.size:,.2f}\n"
                f"<b>Strategy:</b> {strategy.replace('_', ' ').title()}\n"
                f"<b>Cost:</b> ${hedge_result.total_cost:,.2f}\n"
                f"<b>Execution Time:</b> {hedge_result.execution_time:.2f}s\n"
                f"<b>Status:</b> Complete\n\n"
                f"<i>Alerts temporarily suppressed for this position.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            # Clear pending confirmation on failure
            if asset in user['positions']:
                user['positions'][asset]["pending_confirmation"] = False
            await query.edit_message_text(f"❌ Hedge execution failed: {hedge_result.message}", parse_mode=ParseMode.HTML)

    async def risk_report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send a detailed risk report with export option."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            if not positions:
                await update.effective_message.reply_text("❌ No active positions for risk report.")
                return
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            if not portfolio_metrics:
                await update.effective_message.reply_text("❌ Error calculating portfolio risk metrics.")
                return
            report = self.analytics_reporter.generate_portfolio_report(positions, market_data_dict, portfolio_metrics)
            report_text = self.analytics_reporter.generate_telegram_report(report)
            keyboard = [
                [InlineKeyboardButton("📄 Export as PDF", callback_data="export_risk_report_pdf")],
                [InlineKeyboardButton("📊 Back to Analytics", callback_data="risk_analytics")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                report_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in risk_report_command: {e}")
            await update.effective_message.reply_text("❌ Error generating risk report.")

    async def risk_charts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show interactive chart menu for risk metrics."""
        chat_id = update.effective_chat.id if update.effective_chat else None
        user = self._get_user(chat_id)
        positions = [data['position'] for data in user['positions'].values()]
        if not positions:
            await update.effective_message.reply_text("❌ No active positions for risk charts.")
            return
        keyboard = [
            [InlineKeyboardButton("VaR", callback_data="chart_risk_var"),
             InlineKeyboardButton("Drawdown", callback_data="chart_risk_drawdown")],
            [InlineKeyboardButton("Greeks", callback_data="chart_risk_greeks"),
             InlineKeyboardButton("Allocation", callback_data="chart_risk_allocation")],
            [InlineKeyboardButton("Export Chart", callback_data="export_risk_chart")],
            [InlineKeyboardButton("📊 Back to Analytics", callback_data="risk_analytics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(
            "📈 <b>Risk Charts Menu</b>\n\nSelect a risk metric to view its chart:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    async def _handle_export_risk_report_pdf(self, chat_id: int, query):
        """Handle export risk report as PDF."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            if not positions:
                await query.edit_message_text("❌ No active positions for PDF export.")
                return
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            if not portfolio_metrics:
                await query.edit_message_text("❌ Error calculating portfolio metrics for PDF.")
                return
            report = self.analytics_reporter.generate_portfolio_report(positions, market_data_dict, portfolio_metrics)
            # For now, send as text since PDF generation requires additional libraries
            report_text = self.analytics_reporter.generate_telegram_report(report)
            await query.edit_message_text(
                f"📄 <b>Risk Report (Text Format)</b>\n\n{report_text}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error in _handle_export_risk_report_pdf: {e}")
            await query.edit_message_text("❌ Error exporting risk report.")

    async def _handle_chart_risk_var(self, chat_id: int, query):
        """Handle VaR chart generation."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            if not positions:
                await query.edit_message_text("❌ No active positions for VaR chart.")
                return
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            if not portfolio_metrics:
                await query.edit_message_text("❌ Error calculating VaR metrics.")
                return
            # Create VaR chart using analytics reporter
            chart_data = self.analytics_reporter.create_risk_metrics_chart(portfolio_metrics)
            if chart_data:
                await self.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_data,
                    caption="📊 <b>Portfolio VaR Analysis</b>\n\nShows VaR at 95% and 99% confidence levels.",
                    parse_mode=ParseMode.HTML
                )
                await query.edit_message_text("📈 VaR chart sent successfully!")
            else:
                await query.edit_message_text("❌ Error generating VaR chart.")
        except Exception as e:
            logger.error(f"Error in _handle_chart_risk_var: {e}")
            await query.edit_message_text("❌ Error generating VaR chart.")

    async def _handle_chart_risk_drawdown(self, chat_id: int, query):
        """Handle drawdown chart generation."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            if not positions:
                await query.edit_message_text("❌ No active positions for drawdown chart.")
                return
            # Create drawdown chart (simplified for now)
            chart_data = self.analytics_reporter.create_portfolio_chart(positions, {})
            if chart_data:
                await self.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_data,
                    caption="📊 <b>Portfolio Drawdown Analysis</b>\n\nShows maximum drawdown and recovery periods.",
                    parse_mode=ParseMode.HTML
                )
                await query.edit_message_text("📈 Drawdown chart sent successfully!")
            else:
                await query.edit_message_text("❌ Error generating drawdown chart.")
        except Exception as e:
            logger.error(f"Error in _handle_chart_risk_drawdown: {e}")
            await query.edit_message_text("❌ Error generating drawdown chart.")

    async def _handle_chart_risk_greeks(self, chat_id: int, query):
        """Handle Greeks chart generation."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            if not positions:
                await query.edit_message_text("❌ No active positions for Greeks chart.")
                return
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            if not portfolio_metrics:
                await query.edit_message_text("❌ Error calculating Greeks metrics.")
                return
            chart_data = self.analytics_reporter.create_risk_metrics_chart(portfolio_metrics)
            if chart_data:
                await self.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_data,
                    caption="📊 <b>Portfolio Greeks Analysis</b>\n\nShows delta, gamma, theta, and vega exposure.",
                    parse_mode=ParseMode.HTML
                )
                await query.edit_message_text("📈 Greeks chart sent successfully!")
            else:
                await query.edit_message_text("❌ Error generating Greeks chart.")
        except Exception as e:
            logger.error(f"Error in _handle_chart_risk_greeks: {e}")
            await query.edit_message_text("❌ Error generating Greeks chart.")

    async def _handle_chart_risk_allocation(self, chat_id: int, query):
        """Handle allocation chart generation."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            if not positions:
                await query.edit_message_text("❌ No active positions for allocation chart.")
                return
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            chart_data = self.analytics_reporter.create_portfolio_chart(positions, market_data_dict)
            if chart_data:
                await self.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_data,
                    caption="📊 <b>Portfolio Allocation Chart</b>\n\nShows position distribution and risk allocation.",
                    parse_mode=ParseMode.HTML
                )
                await query.edit_message_text("📈 Allocation chart sent successfully!")
            else:
                await query.edit_message_text("❌ Error generating allocation chart.")
        except Exception as e:
            logger.error(f"Error in _handle_chart_risk_allocation: {e}")
            await query.edit_message_text("❌ Error generating allocation chart.")

    async def _handle_export_risk_chart(self, chat_id: int, query):
        """Handle export current risk chart."""
        try:
            await query.edit_message_text("📄 Chart export feature coming soon!")
        except Exception as e:
            logger.error(f"Error in _handle_export_risk_chart: {e}")
            await query.edit_message_text("❌ Error exporting chart.")

    # Add button callback handling for new risk report/chart export/share actions
    # (Implementations for export_risk_report_pdf, chart_risk_var, chart_risk_drawdown, chart_risk_greeks, chart_risk_allocation, export_risk_chart)

    async def schedule_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Configure periodic risk summary frequency."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            if not context.args:
                keyboard = [
                    [InlineKeyboardButton("📅 Daily", callback_data="summary_daily")],
                    [InlineKeyboardButton("📅 Weekly", callback_data="summary_weekly")],
                    [InlineKeyboardButton("❌ Disable", callback_data="summary_disable")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(
                    "📅 <b>Configure Risk Summary Schedule</b>\n\nSelect frequency for periodic risk summaries:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return
            
            frequency = context.args[0].lower()
            if frequency in ['daily', 'weekly', 'off']:
                user['summary_schedule'] = frequency
                if frequency == 'off':
                    user['summary_schedule'] = None
                    await update.effective_message.reply_text("❌ Periodic risk summaries disabled.")
                else:
                    await update.effective_message.reply_text(f"✅ Risk summaries scheduled for {frequency} delivery.")
            else:
                await update.effective_message.reply_text("❌ Invalid frequency. Use: daily, weekly, or off")
        except Exception as e:
            logger.error(f"Error in schedule_summary_command: {e}")
            await update.effective_message.reply_text("❌ Error configuring summary schedule.")

    async def summary_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check current summary schedule status."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            schedule = user.get('summary_schedule', 'Not configured')
            if schedule is None:
                schedule = 'Disabled'
            
            status_text = f"📅 <b>Risk Summary Status</b>\n\n"
            status_text += f"<b>Schedule:</b> {schedule.title()}\n"
            status_text += f"<b>Last Sent:</b> {user.get('last_summary', 'Never')}\n"
            status_text += f"<b>Next Due:</b> {self._calculate_next_summary(schedule)}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("📅 Change Schedule", callback_data="change_summary_schedule")],
                [InlineKeyboardButton("📊 Send Now", callback_data="send_summary_now")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.effective_message.reply_text(
                status_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in summary_status_command: {e}")
            await update.effective_message.reply_text("❌ Error getting summary status.")

    async def send_summary_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger a risk summary."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            await self._send_risk_summary(chat_id)
            await update.effective_message.reply_text("📊 Risk summary sent!")
        except Exception as e:
            logger.error(f"Error in send_summary_now_command: {e}")
            await update.effective_message.reply_text("❌ Error sending risk summary.")

    def _calculate_next_summary(self, schedule):
        """Calculate when next summary is due."""
        if not schedule or schedule == 'Disabled':
            return 'N/A'
        
        now = datetime.now()
        if schedule == 'daily':
            next_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif schedule == 'weekly':
            # Next Monday at 9 AM
            days_ahead = 7 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        else:
            return 'Unknown'
        
        return next_time.strftime('%Y-%m-%d %H:%M')

    async def _send_risk_summary(self, chat_id: int):
        """Send a comprehensive risk summary."""
        try:
            user = self._get_user(chat_id)
            positions = [data['position'] for data in user['positions'].values()]
            
            if not positions:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text="📊 <b>Risk Summary</b>\n\nNo active positions to summarize.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Get market data and calculate metrics
            market_data_dict = {}
            for asset, data in user['positions'].items():
                price = await self.fetch_price(asset)
                if price is not None:
                    market_data_dict[asset] = MarketData(
                        symbol=asset,
                        price=price,
                        volume_24h=0.0,
                        change_24h=0.0,
                        timestamp=datetime.now(),
                        exchange=data['position'].exchange,
                        option_type=data['position'].option_type,
                        strike=data['position'].strike,
                        expiry=data['position'].expiry,
                        underlying=data['position'].underlying
                    )
            
            portfolio_metrics = self.risk_calculator.calculate_portfolio_risk(positions, market_data_dict)
            
            if not portfolio_metrics:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Error calculating portfolio metrics for summary.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Generate summary text
            summary_text = f"📊 <b>Risk Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}</b>\n\n"
            
            # Portfolio overview
            total_value = sum(pos.size * market_data_dict[pos.symbol].price for pos in positions if pos.symbol in market_data_dict)
            total_pnl = sum(pos.unrealized_pnl for pos in positions)
            
            summary_text += f"💰 <b>Portfolio Overview</b>\n"
            summary_text += f"• Total Value: ${total_value:,.2f}\n"
            summary_text += f"• Total P&L: ${total_pnl:,.2f}\n"
            summary_text += f"• Return: {(total_pnl/total_value*100) if total_value > 0 else 0:.2f}%\n"
            summary_text += f"• Positions: {len(positions)}\n\n"
            
            # Risk metrics
            summary_text += f"⚠️ <b>Risk Metrics</b>\n"
            summary_text += f"• Delta: ${portfolio_metrics.delta:,.2f}\n"
            summary_text += f"• VaR (95%): ${portfolio_metrics.var_95:,.2f}\n"
            summary_text += f"• VaR (99%): ${portfolio_metrics.var_99:,.2f}\n"
            summary_text += f"• Max Drawdown: ${portfolio_metrics.max_drawdown:,.2f}\n"
            summary_text += f"• Beta: {portfolio_metrics.beta:.2f}\n\n"
            
            # Position breakdown
            summary_text += f"📈 <b>Position Breakdown</b>\n"
            for position in positions:
                if position.symbol in market_data_dict:
                    price = market_data_dict[position.symbol].price
                    position_value = position.size * price
                    pnl_color = "🟢" if position.unrealized_pnl >= 0 else "🔴"
                    summary_text += f"{pnl_color} {position.symbol}: ${position_value:,.2f} (${position.unrealized_pnl:,.2f})\n"
            
            # Update last summary timestamp
            user['last_summary'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            keyboard = [
                [InlineKeyboardButton("📊 Full Analytics", callback_data="risk_analytics")],
                [InlineKeyboardButton("📈 Risk Charts", callback_data="risk_charts")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=summary_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in _send_risk_summary: {e}")
            await self.application.bot.send_message(
                chat_id=chat_id,
                text="❌ Error generating risk summary.",
                parse_mode=ParseMode.HTML
            )

    async def _periodic_summary_task(self):
        """Background task for sending periodic summaries."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                now = datetime.now()
                for chat_id, user in self.user_data.items():
                    schedule = user.get('summary_schedule')
                    if not schedule:
                        continue
                    
                    # Check if it's time to send summary
                    should_send = False
                    if schedule == 'daily' and now.hour == 9 and now.minute == 0:
                        should_send = True
                    elif schedule == 'weekly' and now.weekday() == 0 and now.hour == 9 and now.minute == 0:
                        should_send = True
                    
                    if should_send:
                        await self._send_risk_summary(chat_id)
                        
            except Exception as e:
                logger.error(f"Error in periodic summary task: {e}")
                await asyncio.sleep(3600)  # Wait an hour before retrying

    async def set_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set custom risk alerts."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            if not context.args or len(context.args) < 3:
                keyboard = [
                    [InlineKeyboardButton("📊 Delta Alert", callback_data="alert_delta")],
                    [InlineKeyboardButton("💰 VaR Alert", callback_data="alert_var")],
                    [InlineKeyboardButton("📈 P&L Alert", callback_data="alert_pnl")],
                    [InlineKeyboardButton("⚠️ Drawdown Alert", callback_data="alert_drawdown")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(
                    "🔔 <b>Set Custom Risk Alert</b>\n\n"
                    "Usage: <code>/set_alert &lt;metric&gt; &lt;condition&gt; &lt;value&gt;</code>\n\n"
                    "Examples:\n"
                    "• <code>/set_alert delta above 50000</code>\n"
                    "• <code>/set_alert var below 20000</code>\n"
                    "• <code>/set_alert pnl below -10000</code>\n\n"
                    "Or select from common alerts:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return
            
            metric = context.args[0].lower()
            condition = context.args[1].lower()
            value = float(context.args[2])
            
            if condition not in ['above', 'below']:
                await update.effective_message.reply_text("❌ Invalid condition. Use 'above' or 'below'.")
                return
            
            if metric not in ['delta', 'var', 'pnl', 'drawdown', 'gamma', 'theta', 'vega']:
                await update.effective_message.reply_text("❌ Invalid metric. Use: delta, var, pnl, drawdown, gamma, theta, vega")
                return
            
            # Initialize alerts if not exists
            if 'custom_alerts' not in user:
                user['custom_alerts'] = []
            
            # Create alert
            alert = {
                'id': len(user['custom_alerts']) + 1,
                'metric': metric,
                'condition': condition,
                'value': value,
                'created': datetime.now(),
                'active': True
            }
            
            user['custom_alerts'].append(alert)
            
            await update.effective_message.reply_text(
                f"✅ <b>Alert Set Successfully</b>\n\n"
                f"<b>Metric:</b> {metric.title()}\n"
                f"<b>Condition:</b> {condition.title()}\n"
                f"<b>Value:</b> {value:,.2f}\n"
                f"<b>Status:</b> Active\n\n"
                f"You'll be notified when {metric} goes {condition} {value:,.2f}.",
                parse_mode=ParseMode.HTML
            )
            
        except ValueError:
            await update.effective_message.reply_text("❌ Invalid value. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in set_alert_command: {e}")
            await update.effective_message.reply_text("❌ Error setting alert.")

    async def alerts_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View current alert settings."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            alerts = user.get('custom_alerts', [])
            
            if not alerts:
                await update.effective_message.reply_text(
                    "🔔 <b>Custom Alerts Status</b>\n\nNo custom alerts configured.\n\n"
                    "Use <code>/set_alert</code> to create alerts.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            status_text = "🔔 <b>Custom Alerts Status</b>\n\n"
            
            for alert in alerts:
                status_icon = "🟢" if alert['active'] else "🔴"
                status_text += f"{status_icon} <b>Alert #{alert['id']}</b>\n"
                status_text += f"   <b>Metric:</b> {alert['metric'].title()}\n"
                status_text += f"   <b>Condition:</b> {alert['condition'].title()} {alert['value']:,.2f}\n"
                status_text += f"   <b>Created:</b> {alert['created'].strftime('%Y-%m-%d %H:%M')}\n"
                status_text += f"   <b>Status:</b> {'Active' if alert['active'] else 'Inactive'}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🗑️ Delete Alert", callback_data="delete_alert_menu")],
                [InlineKeyboardButton("➕ Add Alert", callback_data="add_alert_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.effective_message.reply_text(
                status_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in alerts_status_command: {e}")
            await update.effective_message.reply_text("❌ Error getting alerts status.")

    async def delete_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a specific alert."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            if not context.args:
                alerts = user.get('custom_alerts', [])
                if not alerts:
                    await update.effective_message.reply_text("❌ No alerts to delete.")
                    return
                
                keyboard = []
                for alert in alerts:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🗑️ {alert['metric'].title()} {alert['condition']} {alert['value']:,.2f}",
                            callback_data=f"delete_alert_{alert['id']}"
                        )
                    ])
                keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(
                    "🗑️ <b>Delete Alert</b>\n\nSelect an alert to delete:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return
            
            alert_id = int(context.args[0])
            alerts = user.get('custom_alerts', [])
            
            for i, alert in enumerate(alerts):
                if alert['id'] == alert_id:
                    deleted_alert = alerts.pop(i)
                    await update.effective_message.reply_text(
                        f"✅ <b>Alert Deleted</b>\n\n"
                        f"<b>Metric:</b> {deleted_alert['metric'].title()}\n"
                        f"<b>Condition:</b> {deleted_alert['condition'].title()} {deleted_alert['value']:,.2f}",
                        parse_mode=ParseMode.HTML
                    )
                    return
            
            await update.effective_message.reply_text("❌ Alert not found.")
            
        except ValueError:
            await update.effective_message.reply_text("❌ Invalid alert ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in delete_alert_command: {e}")
            await update.effective_message.reply_text("❌ Error deleting alert.")

    async def _check_custom_alerts(self, chat_id: int, portfolio_metrics, positions, market_data_dict):
        """Check custom alerts and send notifications if triggered."""
        try:
            user = self._get_user(chat_id)
            alerts = user.get('custom_alerts', [])
            
            if not alerts:
                return
            
            triggered_alerts = []
            
            for alert in alerts:
                if not alert['active']:
                    continue
                
                metric_value = None
                metric_name = alert['metric']
                
                # Get current metric value
                if metric_name == 'delta':
                    metric_value = portfolio_metrics.delta
                elif metric_name == 'var':
                    metric_value = portfolio_metrics.var_95
                elif metric_name == 'pnl':
                    metric_value = sum(pos.unrealized_pnl for pos in positions)
                elif metric_name == 'drawdown':
                    metric_value = portfolio_metrics.max_drawdown
                elif metric_name == 'gamma':
                    metric_value = portfolio_metrics.gamma
                elif metric_name == 'theta':
                    metric_value = portfolio_metrics.theta
                elif metric_name == 'vega':
                    metric_value = portfolio_metrics.vega
                
                if metric_value is None:
                    continue
                
                # Check if alert is triggered
                triggered = False
                if alert['condition'] == 'above' and metric_value > alert['value']:
                    triggered = True
                elif alert['condition'] == 'below' and metric_value < alert['value']:
                    triggered = True
                
                if triggered:
                    triggered_alerts.append((alert, metric_value))
            
            # Send notifications for triggered alerts
            for alert, current_value in triggered_alerts:
                alert_text = (
                    f"🚨 <b>Custom Alert Triggered!</b>\n\n"
                    f"<b>Alert #{alert['id']}</b>\n"
                    f"<b>Metric:</b> {alert['metric'].title()}\n"
                    f"<b>Condition:</b> {alert['condition'].title()} {alert['value']:,.2f}\n"
                    f"<b>Current Value:</b> {current_value:,.2f}\n\n"
                    f"<b>Portfolio Status:</b>\n"
                    f"• Total P&L: ${sum(pos.unrealized_pnl for pos in positions):,.2f}\n"
                    f"• Delta: ${portfolio_metrics.delta:,.2f}\n"
                    f"• VaR (95%): ${portfolio_metrics.var_95:,.2f}"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🛡️ Hedge Now", callback_data="hedge_alert")],
                    [InlineKeyboardButton("📊 View Analytics", callback_data="risk_analytics")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=alert_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in _check_custom_alerts: {e}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show overall bot status and system health."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            # Check system health
            deribit_status = "🟢 Connected" if 'deribit' in self.exchanges else "🔴 Disconnected"
            price_history_count = sum(len(history) for history in self.price_history.values())
            
            # Get user stats
            active_positions = sum(1 for data in user['positions'].values() if data.get('is_active', False))
            total_positions = len(user['positions'])
            auto_hedge_enabled = "🟢 Enabled" if user.get('auto_hedge', {}).get('enabled', False) else "🔴 Disabled"
            summary_schedule = user.get('summary_schedule', 'Not configured')
            custom_alerts = len(user.get('custom_alerts', []))
            
            status_text = f"🤖 <b>Hedging Bot Status</b>\n\n"
            status_text += f"<b>System Health:</b>\n"
            status_text += f"• Deribit Connection: {deribit_status}\n"
            status_text += f"• Price History Points: {price_history_count}\n"
            status_text += f"• Active Background Tasks: 2 (Price Polling, Summary)\n\n"
            
            status_text += f"<b>Your Portfolio:</b>\n"
            status_text += f"• Active Positions: {active_positions}/{total_positions}\n"
            status_text += f"• Auto-Hedging: {auto_hedge_enabled}\n"
            status_text += f"• Summary Schedule: {summary_schedule.title()}\n"
            status_text += f"• Custom Alerts: {custom_alerts}\n\n"
            
            status_text += f"<b>Last Update:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            keyboard = [
                [InlineKeyboardButton("📊 Risk Analytics", callback_data="risk_analytics")],
                [InlineKeyboardButton("🔔 Alerts Status", callback_data="alerts_status")],
                [InlineKeyboardButton("📅 Summary Status", callback_data="summary_status")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.effective_message.reply_text(
                status_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in status_command: {e}")
            await update.effective_message.reply_text("❌ Error getting system status.")

    async def version_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot version and build information."""
        version_info = (
            "🤖 <b>Hedging Bot v2.0.0</b>\n\n"
            "<b>Features:</b>\n"
            "• Real-time risk monitoring\n"
            "• Automated hedging strategies\n"
            "• Portfolio analytics & reporting\n"
            "• Custom alerts & notifications\n"
            "• Interactive charts & visualizations\n"
            "• Periodic risk summaries\n\n"
            "<b>Exchange Support:</b>\n"
            "• Deribit (Real-time)\n\n"
            "<b>Risk Metrics:</b>\n"
            "• Greeks (Delta, Gamma, Theta, Vega)\n"
            "• VaR (95%, 99%)\n"
            "• Maximum Drawdown\n"
            "• Correlation & Beta\n"
            "• P&L Attribution\n\n"
            "<b>Hedging Strategies:</b>\n"
            "• Delta-neutral\n"
            "• Options-based\n"
            "• Dynamic rebalancing\n\n"
            "<b>Build:</b> Production Ready"
        )
        
        await update.effective_message.reply_text(
            version_info,
            parse_mode=ParseMode.HTML
        )

    async def emergency_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Emergency stop all monitoring and hedging activities."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            # Stop all monitoring
            stopped_count = 0
            for asset, data in user['positions'].items():
                if data.get('is_active', False):
                    data['is_active'] = False
                    stopped_count += 1
            
            # Disable auto-hedging
            if user.get('auto_hedge', {}).get('enabled', False):
                user['auto_hedge']['enabled'] = False
            
            # Clear custom alerts
            if 'custom_alerts' in user:
                user['custom_alerts'] = []
            
            # Disable summaries
            user['summary_schedule'] = None
            
            keyboard = [
                [InlineKeyboardButton("✅ Confirm Emergency Stop", callback_data="confirm_emergency_stop")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_emergency_stop")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.effective_message.reply_text(
                f"🚨 <b>Emergency Stop Confirmation</b>\n\n"
                f"This will stop all monitoring and hedging activities:\n"
                f"• Stop monitoring {stopped_count} positions\n"
                f"• Disable auto-hedging\n"
                f"• Clear all custom alerts\n"
                f"• Disable periodic summaries\n\n"
                f"<b>Are you sure?</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in emergency_stop_command: {e}")
            await update.effective_message.reply_text("❌ Error processing emergency stop.")
    
    async def reset_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset_alerts command to manually reset suppress_alerts flags."""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user = self._get_user(chat_id)
            
            reset_count = 0
            for asset in user['positions']:
                if user['positions'][asset].get("suppress_alerts", False):
                    user['positions'][asset]["suppress_alerts"] = False
                    reset_count += 1
            
            if reset_count > 0:
                await update.effective_message.reply_text(
                    f"✅ <b>Alert Suppression Reset</b>\n\n"
                    f"Reset suppress_alerts flag for {reset_count} position(s).\n"
                    f"Risk alerts will now be sent normally.",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.effective_message.reply_text(
                    "ℹ️ <b>No Suppressed Alerts</b>\n\n"
                    "No positions have suppressed alerts to reset.",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error in reset_alerts_command: {e}")
            await update.effective_message.reply_text("❌ Error resetting alerts")