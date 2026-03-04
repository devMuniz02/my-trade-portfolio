import os
import requests
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.animation as animation
import numpy as np
from matplotlib.patches import FancyBboxPatch
# Add dotenv support
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- 1) Data Fetching ---
def get_data():
    DATA_API = "https://data-api.polymarket.com"
    WALLET = os.environ.get("WALLET")
    FUNDS = float(os.environ.get("FUNDS", 0))
    if not WALLET or FUNDS <= 0:
        print("Please set WALLET and FUNDS environment variables.")
        return None, None, None
    
    try:
        r_act = requests.get(f"{DATA_API}/activity", params={"user": WALLET}, timeout=20).json()
        r_traded = requests.get(f"{DATA_API}/traded", params={"user": WALLET}, timeout=20).json().get("traded", 0)
    except Exception:
        return ["DAY", "WEEK", "MONTH", "ALL"], [0, 0, 0, 0], [0, 0, 0, 0]

    now = datetime.now(timezone.utc)
    intervals = {
        "DAY": now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc),
        "WEEK": now - timedelta(days=7),
        "MONTH": now - timedelta(days=30),
        "ALL": datetime.min.replace(tzinfo=timezone.utc),
    }

    redeem_counts = {k: 0 for k in intervals}
    for act in r_act:
        if act.get("type") == "REDEEM":
            ts = datetime.fromtimestamp(act.get("timestamp"), tz=timezone.utc)
            for period, start_time in intervals.items():
                if ts >= start_time: redeem_counts[period] += 1

    periods = ["DAY", "WEEK", "MONTH", "ALL"]
    roi_data, trade_counts = [], []
    for period in periods:
        url = f"{DATA_API}/v1/leaderboard?category=OVERALL&timePeriod={period}&orderBy=PNL&user={WALLET}"
        try:
            res = requests.get(url, timeout=20).json()
            top = res[0] if isinstance(res, list) and len(res) > 0 else {}
            pnl = float(top.get("pnl", 0) or 0)
            roi = (pnl / FUNDS) * 100 if FUNDS > 0 else 0
        except Exception: roi = 0
        roi_data.append(roi)
        trade_counts.append(redeem_counts[period] + (r_traded - redeem_counts["ALL"]))
    return periods, roi_data, trade_counts

# --- 2) Animation Logic ---
def create_gif(periods, roi_data, trade_counts):
    bg, card, text, subtext = "#0B0F17", "#111827", "#FFFFFF", "#9CA3AF"
    periods, roi_data, trade_counts = periods[::-1], roi_data[::-1], trade_counts[::-1]

    fig, (axh, ax) = plt.subplots(2, 1, figsize=(10, 6.5), dpi=200, facecolor=bg, 
                                  gridspec_kw={"height_ratios": [1.0, 6.0]})
    fig.subplots_adjust(left=0.20, right=0.85, top=0.90, bottom=0.15, hspace=0.1)

    axh.axis("off")
    axh.text(0.5, 0.6, "Portfolio Performance", color=text, fontsize=22, fontweight="bold", ha="center")
    axh.text(0.5, 0.2, f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC", 
             color=subtext, fontsize=12, ha="center")

    ax.set_facecolor(card)
    max_val = float(np.max(np.abs(roi_data)))
    max_range = round((max_val + 15) / 5) * 5
    ax.set_xlim(-max_range, max_range)
    ax.set_ylim(-0.8, len(periods) - 0.2)
    
    # Grid Styling
    ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{int(x)}%'))
    ax.tick_params(axis="x", colors="white", labelsize=12)
    ax.grid(axis='x', linestyle='--', color=subtext, alpha=0.2, zorder=1)
    ax.axvline(0, color=subtext, lw=1.5, alpha=0.5, zorder=2)
    ax.set_yticks([]) # Hides actual y-axis line/ticks

    patches, value_labels = [], []
    for i, (p, roi, trades) in enumerate(zip(periods, roi_data, trade_counts)):
        # Period Label (Manual)
        ax.text(-max_range * 0.95, i, p, va="center", fontsize=16, fontweight="bold", color="white")
        
        # Bar
        patch = FancyBboxPatch((0, i - 0.25), 0, 0.5, boxstyle="round,pad=0,rounding_size=0.1", 
                               facecolor="#22C55E" if roi >= 0 else "#EF4444", zorder=3)
        ax.add_patch(patch)
        patches.append(patch)
        
        # Incrementing Value Label
        label = ax.text(0.5, i, "+0.0%\n0 trades", va="center", ha="left", 
                        fontsize=12, fontweight="bold", color="white", linespacing=1.6)
        value_labels.append(label)

    def update(frame):
        rise_frames = 60 # 2 seconds
        progress = min(frame / rise_frames, 1.0)
        
        for i, (patch, label, roi, trades) in enumerate(zip(patches, value_labels, roi_data, trade_counts)):
            current_roi = roi * progress
            current_trades = int(trades * progress)
            
            # Bar width
            width = abs(current_roi)
            patch.set_width(width)
            patch.set_x(0 if roi >= 0 else -width)
            
            # Text update
            x_pos = (current_roi + (0.5 if roi >= 0 else -0.5))
            label.set_x(x_pos)
            label.set_ha("left" if roi >= 0 else "right")
            label.set_text(f"{current_roi:+.1f}%\n{current_trades} trades")
            
        return patches + value_labels

    anim = animation.FuncAnimation(fig, update, frames=210, interval=33.3)
    output_path = os.path.join(os.path.dirname(__file__), "..", "assets", "performance_animation.gif")
    output_path = os.path.abspath(output_path)
    anim.save(output_path, writer="pillow", fps=30)
    print(f"GIF saved as {output_path}")

if __name__ == "__main__":
    p, r, t = get_data()
    if p is None:
        print("Data fetching failed. Please check your environment variables and try again.")
    else:
        create_gif(p, r, t)