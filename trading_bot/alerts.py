import logging
import requests
from trading_bot.network import SourceAddressAdapter

class AlertManager:
    """Sends critical alerts via Webhook (Telegram/Slack)"""
    def __init__(self, webhook_url: str, logger: logging.Logger, source_ip: str = None, proxy_url: str = None):
        self.webhook_url = webhook_url
        self.logger = logger
        self.source_ip = source_ip
        self.proxy_url = proxy_url
        
        # Configure Session with Network Settings
        self.session = requests.Session()
        if source_ip or proxy_url:
            self.logger.debug(f"[ALERT] Configuring AlertManager with Net settings: {'EIP' if source_ip else 'Proxy'}")
            if source_ip:
                import socket
                is_bindable = False
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind((source_ip, 0))
                    s.close()
                    is_bindable = True
                except Exception:
                    self.logger.warning(f"[ALERT] Webhook Source IP {source_ip} is not present/bindable on this host. Routing alert webhook through default interface.")
                
                if is_bindable:
                    adapter = SourceAddressAdapter(source_address=(source_ip, 0))
                    self.session.mount("http://", adapter)
                    self.session.mount("https://", adapter)
            if proxy_url:
                self.session.proxies = {'http': proxy_url, 'https': proxy_url}

    def send_alert(self, message: str, header: str = "Algo Alert"):
        if not self.webhook_url:
            self.logger.debug("Alert ignored: No Webhook URL configured.")
            return

        try:
            # Select Emoji based on Header
            emoji = "🚨"
            if any(x in header for x in ["Trade", "Order", "EXEC"]): emoji = "💰"
            elif any(x in header for x in ["Digest", "Report", "Summary", "PnL", "Risk"]): emoji = "📊"
            elif any(x in header for x in ["Start", "Initial", "Ready"]): emoji = "🟢"
            elif any(x in header for x in ["Stop", "Close", "SQ_OFF", "Shutdown"]): emoji = "🛑"
            
            payload = {"text": f"{emoji} *{header}*\n{message}"}
            # Handle Slack vs Telegram (Basic JSON post works for Slack/Teams, Telegram needs chat_id in query params)
            resp = self.session.post(self.webhook_url, json=payload, timeout=5)

            if resp.status_code >= 400:
                self.logger.error(f"Failed to send alert. Status: {resp.status_code}")
        except Exception as e:
            self.logger.error(f"Alert Webhook Error: {e}")
