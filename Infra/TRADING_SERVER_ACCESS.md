# Dedicated Quant & Algorithmic Trading Server Access

## Server Overview
This dedicated Linux server is provisioned for running multi-threaded algorithmic trading bots, quantitative research, backtesting, and market-making strategies.

- **Direct Alias**: `ssh trading` (Passwordless, configured with your SSH key)
- **Host IP**: `100.86.87.19` (Tailscale Private Network)
- **Port**: `7742`
- **Username**: `rohan`
- **Authentication**: Key-based (`~/.ssh/id_ed25519`) or Password (`r00t`)

---

## Hardware & Compute Capacity
- **CPU**: AMD Ryzen 5 7535HS (6 Physical Zen 3+ Cores / 12 Threads @ up to 4.55 GHz)
- **Architecture**: Native `x86_64` (Full compatibility with all C++/Python quant libraries and TA-Lib)
- **Memory**: 11 GB RAM + 4 GB Swap (~7.0 GB free and idle)
- **Storage**: 880 GB Free NVMe SSD Storage
- **Operating System**: Ubuntu 24.04.3 LTS with native `systemd`

---

## How to Connect

### 1. From Any Terminal inside your Workspace (`myapps.rohan.run.place`):
Simply open any terminal (Warp, xterm, or Antigravity IDE terminal) and run:
```bash
ssh trading
```
*Your SSH key is already installed and authorized. No password required!*

### 2. Manual SSH Connection (from external machines on Tailscale):
```bash
ssh -p 7742 rohan@100.86.87.19
```

---

## Pre-Configured Trading Environment on Server
The server has been structured specifically for trading operations:

- **Trading Root Directory**: `~/trading/`
  - `~/trading/bots/`: Live trading bot scripts and execution daemons
  - `~/trading/strategies/`: Strategy formulations, alpha signals, indicators
  - `~/trading/data/`: Historical OHLCV market data & tick databases
  - `~/trading/logs/`: Trade execution logs and audit trails
  - `~/trading/venv/`: Dedicated Python 3.12 Virtual Environment

### Activating the Python Environment:
```bash
source ~/trading/venv/bin/activate
```
*Pre-installed packages: `numpy`, `pandas`, `scipy`, `ccxt`, `requests`, `websockets`, `python-dotenv`.*

---

## Running Trading Bots 24/7 (Background Execution)

### Option A: Using `tmux` (Interactive)
```bash
# Start a new trading session:
tmux new -s live-bot

# Inside tmux, activate environment and start bot:
source ~/trading/venv/bin/activate
python ~/trading/bots/my_bot.py

# Detach from session: Press Ctrl+B, then release and press D
# Reattach later anytime:
tmux attach -t live-bot
```

### Option B: Using `systemd` (Automatic 24/7 Service with Auto-Restart)
Create a service file at `~/.config/systemd/user/trading-bot.service`:
```ini
[Unit]
Description=My Live Trading Bot
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/trading
ExecStart=%h/trading/venv/bin/python %h/trading/bots/my_bot.py
Restart=always
RestartSec=5
StandardOutput=append:%h/trading/logs/bot.log
StandardError=append:%h/trading/logs/bot.err.log

[Install]
WantedBy=default.target
```
Enable and start the service:
```bash
systemctl --user daemon-reload
systemctl --user enable --now trading-bot.service
systemctl --user status trading-bot.service
```

---

## Operational Notes
- **Direct Network Access**: Traffic does not pass through any proxy or filter; you have direct raw socket and WebSocket access to exchange APIs.
- **Latency**: Round-trip ping to Zerodha Kite and Upstox is ~30–34 ms.
