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
POSITIVE_CASH_ACTIVITY_TYPES = {"REDEEM", "REWARD", "REFERRAL_REWARD", "MAKER_REBATE"}
POLYGON_RPC_URLS = [
    os.environ.get("POLYGON_RPC_URL", "").strip(),
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon.drpc.org",
]
PUSD_TOKEN_ADDRESS = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"


def get_period_starts(now):
    return {
        "DAY": now - timedelta(days=1),
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


def fetch_current_cash_balance(wallet):
    wallet_hex = wallet.lower().removeprefix("0x")
    if len(wallet_hex) != 40:
        raise ValueError("Wallet address must be 20 bytes.")

    method_selector = "70a08231"  # balanceOf(address)
    padded_wallet = wallet_hex.rjust(64, "0")
    call_data = f"0x{method_selector}{padded_wallet}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": PUSD_TOKEN_ADDRESS, "data": call_data},
            "latest",
        ],
    }

    errors = []
    for rpc_url in POLYGON_RPC_URLS:
        if not rpc_url:
            continue

        try:
            response = requests.post(rpc_url, json=payload, timeout=20)
            response.raise_for_status()
            body = response.json()
            result = body.get("result")
            if isinstance(result, str):
                raw_balance = int(result, 16)
                return raw_balance / 1_000_000
            errors.append(f"{rpc_url}: {body}")
        except Exception as exc:
            errors.append(f"{rpc_url}: {exc}")

    raise RuntimeError("Unable to fetch pUSD balance. " + " | ".join(errors))


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
            params={"user": wallet, "limit": 500, "offset": offset, "sizeThreshold": 0},
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


def build_current_position_lookup(positions):
    current_lookup = {}
    for item in positions:
        asset = item.get("asset")
        if not asset:
            continue
        current_lookup[asset] = {
            "size": float(item.get("size", 0) or 0),
            "value": float(item.get("currentValue", 0) or 0),
            "cur_price": float(item.get("curPrice", 0) or 0),
            "avg_price": float(item.get("avgPrice", 0) or 0),
        }

    return current_lookup


def get_period_trade_activities(activities, start_ts):
    period_activities = []
    for item in activities:
        if not is_trade_activity(item):
            continue

        ts = get_activity_timestamp(item)
        if ts is None or int(ts.timestamp()) < start_ts:
            continue

        period_activities.append(item)

    return period_activities


def calculate_trade_cashflow(trade_activities):
    cashflow = 0.0
    for item in trade_activities:
        side = str(item.get("side", "")).upper()
        usdc_size = float(item.get("usdcSize", 0) or 0)
        if side == "BUY":
            cashflow -= usdc_size
        elif side == "SELL":
            cashflow += usdc_size
    return cashflow


def calculate_total_cashflow(activities):
    cashflow = 0.0
    for item in activities:
        activity_type = str(item.get("type", "")).upper()
        usdc_size = float(item.get("usdcSize", 0) or 0)

        if activity_type in TRADE_ACTIVITY_TYPES:
            side = str(item.get("side", "")).upper()
            if side == "BUY":
                cashflow -= usdc_size
            elif side == "SELL":
                cashflow += usdc_size
        elif activity_type in POSITIVE_CASH_ACTIVITY_TYPES:
            cashflow += usdc_size

    return cashflow


def calculate_historical_positions_value(current_positions, period_activities, start_ts, now_ts):
    activities_by_asset = {}
    for item in period_activities:
        asset = item.get("asset")
        if not asset:
            continue
        activities_by_asset.setdefault(asset, []).append(item)

    assets = set(current_positions.keys()) | set(activities_by_asset.keys())
    historical_value = 0.0

    for asset in assets:
        current_position = current_positions.get(asset, {})
        current_size = float(current_position.get("size", 0) or 0)
        fallback_price = float(current_position.get("cur_price", 0) or 0)
        if fallback_price <= 0:
            fallback_price = float(current_position.get("avg_price", 0) or 0)

        size_delta = 0.0
        for activity in activities_by_asset.get(asset, []):
            side = str(activity.get("side", "")).upper()
            trade_size = float(activity.get("size", 0) or 0)
            if side == "BUY":
                size_delta += trade_size
            elif side == "SELL":
                size_delta -= trade_size

            if fallback_price <= 0:
                fallback_price = float(activity.get("price", 0) or 0)

        historical_size = current_size - size_delta
        if historical_size <= 0:
            continue

        start_price = get_price_at_period_start(asset, start_ts, now_ts, fallback_price)
        historical_value += historical_size * start_price

    return historical_value


def calculate_period_snapshot(period, current_cash_balance, current_positions_value, current_positions, activities, intervals, now_ts, funds):
    current_total_value = current_cash_balance + current_positions_value

    if period == "ALL":
        baseline_value = funds
        roi = ((current_total_value - baseline_value) / baseline_value) * 100 if baseline_value > 0 else 0
        return {
            "current_total_value": current_total_value,
            "baseline_total_value": baseline_value,
            "baseline_cash_balance": funds,
            "baseline_positions_value": 0.0,
            "roi": roi,
        }

    start_ts = int(intervals[period].timestamp())
    period_activities = get_period_trade_activities(activities, start_ts)
    period_all_activities = []
    for item in activities:
        ts = get_activity_timestamp(item)
        if ts is None or int(ts.timestamp()) < start_ts:
            continue
        period_all_activities.append(item)

    period_cashflow = calculate_total_cashflow(period_all_activities)
    historical_cash_balance = current_cash_balance - period_cashflow
    historical_positions_value = calculate_historical_positions_value(
        current_positions,
        period_activities,
        start_ts,
        now_ts,
    )
    historical_total_value = historical_cash_balance + historical_positions_value

    roi = 0.0
    if historical_total_value > 0:
        roi = ((current_total_value - historical_total_value) / historical_total_value) * 100

    return {
        "current_total_value": current_total_value,
        "baseline_total_value": historical_total_value,
        "baseline_cash_balance": historical_cash_balance,
        "baseline_positions_value": historical_positions_value,
        "roi": roi,
    }


def fetch_metrics():
    DATA_API = "https://data-api.polymarket.com"
    WALLET = os.environ.get("POLYMARKET_PROXY_WALLET") or os.environ.get("WALLET")
    FUNDS = float(os.environ.get("FUNDS", 0))
    if not WALLET or FUNDS <= 0:
        print("Please set WALLET and FUNDS environment variables.")
        return None

    try:
        r_act = fetch_all_activity(DATA_API, WALLET)
        r_traded = fetch_json(f"{DATA_API}/traded", params={"user": WALLET}).get("traded", 0)
        positions = fetch_all_open_positions(DATA_API, WALLET)
        current_cash_balance = fetch_current_cash_balance(WALLET)
    except Exception as exc:
        print(f"Failed to fetch metrics: {exc}")
        return None

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

    now_ts = int(now.timestamp())
    current_positions = build_current_position_lookup(positions)
    current_positions_value = sum(float(position.get("value", 0) or 0) for position in current_positions.values())
    metrics = []
    for period in PERIODS:
        period_snapshot = calculate_period_snapshot(
            period,
            current_cash_balance,
            current_positions_value,
            current_positions,
            r_act,
            intervals,
            now_ts,
            FUNDS,
        )

        metrics.append({
            "period": period,
            "roi": period_snapshot["roi"],
            "trades": trade_counts[period],
            "value_now": period_snapshot["current_total_value"],
            "value_then": period_snapshot["baseline_total_value"],
            "cash_now": current_cash_balance,
            "positions_now": current_positions_value,
            "cash_then": period_snapshot["baseline_cash_balance"],
            "positions_then": period_snapshot["baseline_positions_value"],
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
