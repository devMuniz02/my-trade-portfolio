import os
import requests
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.animation as animation
import numpy as np
from matplotlib.patches import FancyBboxPatch
from dotenv import load_dotenv

load_dotenv()

PERIODS = ["DAY", "WEEK", "MONTH", "ALL"]
TRADE_ACTIVITY_TYPES = {"TRADE"}


def get_period_starts(now):
    return {
        "DAY": now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc),
        "WEEK": now - timedelta(days=7),
        "MONTH": now - timedelta(days=30),
        "ALL": datetime.min.replace(tzinfo=timezone.utc),
    }


def get_activity_timestamp(activity):
    timestamp = activity.get("timestamp")
    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def is_trade_activity(activity):
    return str(activity.get("type", "")).upper() in TRADE_ACTIVITY_TYPES


def fetch_json(url, params=None):
    return requests.get(url, params=params, timeout=20).json()


def fetch_all_activity(base_url, wallet, start=None, end=None):
    items = []
    offset = 0

    while True:
        batch = fetch_json(
            f"{base_url}/activity",
            params={
                "user": wallet,
                "limit": 500,
                "offset": offset,
                "start": start,
                "end": end,
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC",
            },
        )
        if not isinstance(batch, list) or not batch:
            break

        items.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    return items


def fetch_all_closed_positions(base_url, wallet):
    items = []
    offset = 0

    while True:
        batch = fetch_json(
            f"{base_url}/closed-positions",
            params={"user": wallet, "limit": 500, "offset": offset},
        )
        if not isinstance(batch, list) or not batch:
            break

        items.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    return items


def fetch_all_open_positions(base_url, wallet):
    items = []
    offset = 0

    while True:
        batch = fetch_json(
            f"{base_url}/positions",
            params={"user": wallet, "limit": 500, "offset": offset},
        )
        if not isinstance(batch, list) or not batch:
            break

        items.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    return items


def fetch_price_history(asset, start_ts, end_ts):
    try:
        data = fetch_json(
            "https://clob.polymarket.com/prices-history",
            params={
                "market": asset,
                "startTs": start_ts,
                "endTs": end_ts,
                "interval": "1h",
                "fidelity": 60,
            },
        )
    except Exception:
        return []

    history = data.get("history", []) if isinstance(data, dict) else []
    return history if isinstance(history, list) else []


def get_price_at_period_start(asset, start_ts, end_ts, fallback_price):
    history = fetch_price_history(asset, start_ts, end_ts)
    if history:
        return float(history[0].get("p", fallback_price) or fallback_price)
    return fallback_price


def calculate_open_position_period_pnl(position, period_activities, start_ts, end_ts):
    asset = position.get("asset")
    current_size = float(position.get("size", 0) or 0)
    current_value = float(position.get("currentValue", 0) or 0)
    current_price = float(position.get("curPrice", 0) or 0)
    avg_price = float(position.get("avgPrice", 0) or 0)

    size_delta = 0.0
    cashflow = 0.0
    for activity in period_activities:
        if activity.get("asset") != asset or activity.get("type") != "TRADE":
            continue

        side = str(activity.get("side", "")).upper()
        trade_size = float(activity.get("size", 0) or 0)
        usdc_size = float(activity.get("usdcSize", 0) or 0)

        if side == "BUY":
            size_delta += trade_size
            cashflow -= usdc_size
        elif side == "SELL":
            size_delta -= trade_size
            cashflow += usdc_size

    start_size = max(current_size - size_delta, 0.0)
    if start_size <= 0:
        start_value = 0.0
    else:
        fallback_price = current_price if current_price > 0 else avg_price
        start_price = get_price_at_period_start(asset, start_ts, end_ts, fallback_price)
        start_value = start_size * start_price

    return current_value + cashflow - start_value


def calculate_period_pnl(period, positions, closed_positions, activities, intervals, now_ts, funds, all_time_pnl):
    if period == "ALL":
        return all_time_pnl

    start_ts = int(intervals[period].timestamp())
    period_activities = [
        item for item in activities
        if is_trade_activity(item) and (get_activity_timestamp(item) and int(get_activity_timestamp(item).timestamp()) >= start_ts)
    ]

    open_pnl = sum(
        calculate_open_position_period_pnl(position, period_activities, start_ts, now_ts)
        for position in positions
    )

    realized_pnl = 0.0
    for item in closed_positions:
        try:
            timestamp = int(float(item.get("timestamp", 0) or 0))
            if timestamp >= start_ts:
                realized_pnl += float(item.get("realizedPnl", 0) or 0)
        except (TypeError, ValueError):
            continue

    return open_pnl + realized_pnl


def fetch_metrics():
    DATA_API = "https://data-api.polymarket.com"
    WALLET = os.environ.get("WALLET")
    FUNDS = float(os.environ.get("FUNDS", 0))
    if not WALLET or FUNDS <= 0:
        print("Please set WALLET and FUNDS environment variables.")
        return None

    try:
        r_act = fetch_all_activity(DATA_API, WALLET)
        r_traded = fetch_json(f"{DATA_API}/traded", params={"user": WALLET}).get("traded", 0)
        positions = fetch_all_open_positions(DATA_API, WALLET)
        closed_positions = fetch_all_closed_positions(DATA_API, WALLET)
    except Exception:
        return [{"period": period, "roi": 0, "trades": 0} for period in PERIODS]

    now = datetime.now(timezone.utc)
    intervals = get_period_starts(now)
    trade_counts = {period: 0 for period in PERIODS}

    for act in r_act:
        if not is_trade_activity(act):
            continue

        ts = get_activity_timestamp(act)
        if ts is None:
            continue

        for period, start_time in intervals.items():
            if ts >= start_time:
                trade_counts[period] += 1

    try:
        trade_counts["ALL"] = max(trade_counts["ALL"], int(float(r_traded or 0)))
    except (TypeError, ValueError):
        pass

    pnl_by_period = {}
    for period in PERIODS:
        url = f"{DATA_API}/v1/leaderboard?category=OVERALL&timePeriod={period}&orderBy=PNL&user={WALLET}"
        try:
            res = requests.get(url, timeout=20).json()
            top = res[0] if isinstance(res, list) and len(res) > 0 else {}
            pnl_by_period[period] = float(top.get("pnl", 0) or 0)
        except Exception:
            pnl_by_period[period] = 0

    now_ts = int(now.timestamp())
    all_time_pnl = pnl_by_period["ALL"]
    current_portfolio_value = FUNDS + all_time_pnl
    metrics = []
    for period in PERIODS:
        pnl = calculate_period_pnl(period, positions, closed_positions, r_act, intervals, now_ts, FUNDS, all_time_pnl)
        if period == "ALL":
            baseline_value = FUNDS
        else:
            baseline_value = current_portfolio_value - pnl

        roi = (pnl / baseline_value) * 100 if baseline_value > 0 else 0

        metrics.append({
            "period": period,
            "roi": roi,
            "trades": trade_counts[period],
        })

    return metrics


# --- 1) Data Fetching ---
def get_data():
    metrics = fetch_metrics()
    if metrics is None:
        return None, None, None

    periods = [item["period"] for item in metrics]
    roi_data = [item["roi"] for item in metrics]
    trade_counts = [item["trades"] for item in metrics]
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
