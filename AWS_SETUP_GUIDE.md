# AWS Deployment Guide for Dhan Live Trading Bot

This guide assumes you have an AWS EC2 instance running Ubuntu/Linux.

## 1. Prerequisites & Environment Setup
Ensure you have copied the `aws_deployment` folder to your EC2 instance (e.g., inside `/home/ubuntu/`).

### A. Set Timezone to IST (CRITICAL)
```bash
sudo timedatectl set-timezone Asia/Kolkata
timedatectl # Verify it shows IST
```

### B. Install Python 3.12 & Build Virtual Environment
SATP uses Python 3.12 for native compatibility with machine learning packages (`scikit-learn`, `xgboost`, `scipy`, `pandas-ta`).

```bash
cd /home/ubuntu/aws_deployment

# 1. Install Python 3.12 system packages
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3.12-dev build-essential

# 2. Create clean virtual environment
python3.12 -m venv venv
sudo chown -R ubuntu:ubuntu venv
source venv/bin/activate

# 3. Upgrade pip & install requirements without caching (prevents disk-full errors)
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
```

## 2. Environment Variables (.env)
Update your `.env` file in the `aws_deployment` folder to include the `ALERT_WEBHOOK_URL` for Telegram/Slack notifications.

```ini
DHAN_CLIENT_ID="12345678"
DHAN_API_TOKEN="ey..."
ALERT_WEBHOOK_URL="https://api.telegram.org/bot8..."
DHAN_SOURCE_IP=""  # Primary Account Private IP
```

## 3. Multi-Account Networking (CRITICAL)
For brokers like Dhan, you must place trades from a unique whitelisted IP for each account.

### A. Assign Secondary IPs in AWS Console
1. Go to EC2 -> Network Interfaces -> Manage IP Addresses.
2. Add Secondary Private IPs for each extra account.
3. Associate a unique Elastic IP for each Private IP.

### B. Make Routing Permanent (Ubuntu)
Run these commands to ensure your 6+ IPs survive a reboot:

```bash
# 1. Create the persistent routing script
cat << 'EOF' | sudo tee /usr/local/bin/fix-trading-routes.sh
#!/bin/bash
sleep 5
# Restore IPs
sudo ip addr add 10.0.1.33/24 dev ens5 2>/dev/null
sudo ip addr add 10.0.1.27/24 dev ens5 2>/dev/null
sudo ip addr add 10.0.1.183/24 dev ens6 2>/dev/null
sudo ip addr add 10.0.1.244/24 dev ens6 2>/dev/null

# Setup Policy Routing table
grep -q "rt_ens6" /etc/iproute2/rt_tables || echo "100 rt_ens6" >> /etc/iproute2/rt_tables
sudo ip route add 10.0.1.0/24 dev ens6 src 10.0.1.244 table rt_ens6 2>/dev/null
sudo ip route add default via 10.0.1.1 dev ens6 table rt_ens6 2>/dev/null
sudo ip rule add from 10.0.1.244 table rt_ens6 2>/dev/null
sudo ip rule add from 10.0.1.183 table rt_ens6 2>/dev/null
EOF
sudo chmod +x /usr/local/bin/fix-trading-routes.sh

# 2. Create and start the routing service
cat << 'EOF' | sudo tee /etc/systemd/system/trading-routes.service
[Unit]
Description=Fix trading bot routing for secondary ENI
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/fix-trading-routes.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now trading-routes
```

## 4. Set up the Systemd Service
This ensures the bot automatically turns on when the server boots and intelligently handles crashes *without* causing infinite loops.

1. Create a service file:
```bash
sudo nano /etc/systemd/system/live_trade.service
```

2. Add the following configuration (Adjust paths if your username is not `ubuntu`):
```ini
[Unit]
Description=Dhan Live Trading Bot
After=network.target trading-routes.service
Requires=trading-routes.service

# Safe Restart Logic (Prevents API Ban loops)
StartLimitBurst=3
StartLimitIntervalSec=300

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/aws_deployment

# Run the safe maintenance script first (archives state only before 9 AM)
ExecStartPre=/bin/bash /home/ubuntu/aws_deployment/maintenance.sh

# Run the python script
ExecStart=/home/ubuntu/aws_deployment/venv/bin/python /home/ubuntu/aws_deployment/live_trade_fixed.py

# Send all Python print/logging statements to the system journal
StandardOutput=journal
StandardError=journal

# Restart on failure logic
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

3. Reload systemd:
```bash
sudo systemctl daemon-reload

# IMPORTANT: If your EC2 is scheduled to start every morning, DO NOT enable the service. 
# Enabling it will cause the bot to run on weekends when the EC2 boots up.
# To stop your bot from starting on weekends, disable it:
sudo systemctl disable live_trade.service

# DO NOT start it manually right now if it is outside market hours. The Mon-Fri Cron job handles starting and stopping.
```

## 4. Set up Cron Jobs
We use `cron` to enforce strict start/stop times and renew the tokens every 12 hours.

1. Open the crontab:
```bash
crontab -u ubuntu -e
```

2. Add the following lines:
```cron
# 1. Start Bot exactly at 09:10 AM IST (Monday to Friday, if market is open)
10 09 * * 1-5 /home/ubuntu/aws_deployment/venv/bin/python3 /home/ubuntu/aws_deployment/is_market_open.py && /usr/bin/sudo /usr/bin/systemctl start live_trade.service

# 2. Hard Stop Bot exactly at 15:05 PM IST (Monday to Friday)
05 15 * * 1-5 /usr/bin/sudo /usr/bin/systemctl stop live_trade.service

# 3. Target Token Renewal every 12 hours (08:00 AM and 08:00 PM IST)
0 8,20 * * * /home/ubuntu/aws_deployment/venv/bin/python3 /home/ubuntu/aws_deployment/renew_tokens.py >> /home/ubuntu/aws_deployment/token_cron.log 2>&1

# 4. Token Renewal Recovery on Server Boot (handles server restarts gracefully)
@reboot /home/ubuntu/aws_deployment/venv/bin/python3 /home/ubuntu/aws_deployment/renew_tokens.py >> /home/ubuntu/aws_deployment/token_cron.log 2>&1
```

## 5. Monitoring & Logs

**View Live Python Logs:**
```bash
journalctl -u live_trade.service -f
journalctl -u live_trade.service -n 50 #last 50 logs line
```

**View Systemd Restart Status:**
```bash
systemctl status live_trade.service
```

**View Token Renewal Logs:**
```bash
cat /home/ubuntu/aws_deployment/token_cron.log
```

**Restarting the Bot:**
If you receive an error alert via Telegram and need to restart the bot manually (e.g., during market hours):
```bash
sudo systemctl restart live_trade.service
```
This stops the service now and prevents it from starting automatically on reboot or by other systemd events until you re-enable it.
```bash
sudo systemctl disable --now live_trade.service
```

To re-enable it later, run: sudo systemctl enable --now live_trade.service.
```bash
sudo systemctl enable live_trade.service
```

Every time you replace the .env file with a fresh copy, you should re-run the ownership fix to make sure your automation can still use it:

```bash
sudo chown ubuntu:ubuntu /home/ubuntu/aws_deployment/.env
chmod 600 /home/ubuntu/aws_deployment/.env
```

## 6. Testing Order Placement
Before relying on the cron job, verify that your IPs are whitelisted with Dhan.

1. Run the test script:
```bash
source venv/bin/activate
python3 test_order_placement.py
```

2. Expected Result:
You should see "PASS: Your IP is Whitelisted" for each account. If you see "IP Not Whitelisted", you must add that IP to the Dhan Security Settings.

## 7. Troubleshooting

**Bot not starting on Monday morning?**
- Check if the EC2 instance is running.
- Check if the systemd service is enabled: `sudo systemctl is-enabled live_trade.service`
- Check cron logs: `cat /home/ubuntu/aws_deployment/token_cron.log`

**Getting "Permission Denied" for .env?**
- Run: `sudo chown ubuntu:ubuntu /home/ubuntu/aws_deployment/.env`  


su - ubuntu