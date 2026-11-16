import os
import re
import json
import hashlib
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from databricks import sql
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="PulseCrypto | Market Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- GLASSMORPHISM DARK UI & CRYPTO BACKGROUND CSS ---
st.markdown(
    """
    <style>
    /* Deep Obsidian Base */
    .stApp {
        background: radial-gradient(circle at 15% 15%, #0D1B2A 0%, #06090F 45%, #030508 100%);
        color: #F0F6FC;
    }
    .block-container {
        padding-top: 2.6rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1460px;
        position: relative;
        z-index: 2;
    }

    /* Ambient Animated Crypto Mesh Watermark Layer */
    .crypto-bg-orb-1 {
        position: fixed;
        top: -120px;
        left: -100px;
        width: 480px;
        height: 480px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0, 229, 153, 0.11) 0%, transparent 70%);
        filter: blur(40px);
        animation: driftOrb1 16s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }
    .crypto-bg-orb-2 {
        position: fixed;
        bottom: -140px;
        right: -80px;
        width: 540px;
        height: 540px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(56, 139, 253, 0.12) 0%, transparent 70%);
        filter: blur(45px);
        animation: driftOrb2 20s ease-in-out infinite alternate;
        pointer-events: none;
        z-index: 0;
    }
    .crypto-grid-overlay {
        position: fixed;
        inset: 0;
        background-image:
            linear-gradient(rgba(255, 255, 255, 0.022) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.022) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: radial-gradient(ellipse at center, black 45%, transparent 90%);
        pointer-events: none;
        z-index: 0;
    }
    @keyframes driftOrb1 {
        0%   { transform: translate(0px, 0px) scale(1); }
        100% { transform: translate(90px, 60px) scale(1.12); }
    }
    @keyframes driftOrb2 {
        0%   { transform: translate(0px, 0px) scale(1); }
        100% { transform: translate(-80px, -70px) scale(1.15); }
    }

    /* Clean Minimal Title Row (No bulky box or technical pipeline labels) */
    .brand-bar {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 18px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    }
    .brand-title {
        font-size: 1.7rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.02em;
    }
    .brand-accent {
        color: #00E599;
    }
    .brand-sub {
        font-size: 0.88rem;
        color: #8B949E;
    }

    /* Gradient Hero KPI Cards */
    .hero-kpi {
        border-radius: 14px;
        padding: 18px 20px;
        height: 124px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .hero-kpi:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.28);
    }
    .hero-grad-emerald {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.85) 0%, rgba(13, 148, 136, 0.45) 100%);
    }
    .hero-grad-indigo {
        background: linear-gradient(135deg, rgba(49, 46, 129, 0.85) 0%, rgba(124, 58, 237, 0.45) 100%);
    }
    .hero-grad-cyan {
        background: linear-gradient(135deg, rgba(12, 74, 110, 0.85) 0%, rgba(2, 132, 199, 0.45) 100%);
    }
    .hero-grad-amber {
        background: linear-gradient(135deg, rgba(120, 53, 15, 0.85) 0%, rgba(217, 119, 6, 0.45) 100%);
    }
    .hero-kpi-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(248, 250, 252, 0.82);
    }
    .hero-kpi-val {
        font-size: 1.7rem;
        font-weight: 800;
        color: #FFFFFF;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.02em;
    }
    .hero-kpi-sub {
        font-size: 0.8rem;
        color: rgba(248, 250, 252, 0.85);
    }

    /* Uniform Frosted Glass Secondary KPI Cards */
    div[data-testid="stMetric"] {
        background: rgba(13, 17, 23, 0.72) !important;
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 14px 18px !important;
        height: 118px !important;
        min-height: 118px !important;
        max-height: 118px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 6px 22px rgba(0, 0, 0, 0.35);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #00E599 !important;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricLabel"] {
        color: #8B949E !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="stMetricValue"] {
        color: #F0F6FC !important;
        font-size: 1.48rem !important;
        font-weight: 700 !important;
        font-variant-numeric: tabular-nums;
    }

    /* Glass Section Container Title */
    .glass-panel-title {
        font-size: 1.02rem;
        font-weight: 600;
        color: #F0F6FC;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .panel-tag {
        font-size: 0.72rem;
        color: #8B949E;
        background: rgba(255, 255, 255, 0.05);
        padding: 3px 9px;
        border-radius: 6px;
    }

    /* Unified Emerald Action Buttons */
    div.stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #00E599 0%, #00B8D9 100%) !important;
        color: #05070A !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 0.58rem 1rem !important;
        transition: opacity 0.2s ease, transform 0.15s ease;
    }
    div.stButton > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        opacity: 0.9 !important;
        transform: translateY(-1px);
        color: #05070A !important;
    }
    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }

    /* AI Executive Brief Glass Card */
    .ai-brief-card {
        background: rgba(13, 17, 23, 0.78);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #00E599;
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 12px;
        color: #C9D1D9;
        line-height: 1.62;
        font-size: 0.93rem;
    }
    .ai-risk-banner {
        margin-top: 10px;
        padding: 9px 13px;
        background: rgba(248, 81, 73, 0.09);
        border: 1px solid rgba(248, 81, 73, 0.28);
        border-radius: 8px;
        color: #FF7B72;
        font-size: 0.86rem;
    }
    </style>

    <!-- Ambient Background Layers -->
    <div class="crypto-grid-overlay"></div>
    <div class="crypto-bg-orb-1"></div>
    <div class="crypto-bg-orb-2"></div>

    <!-- Clean Product Title -->
    <div class="brand-bar">
        <div class="brand-title">Pulse<span class="brand-accent">Crypto</span> &mdash; Market Intelligence</div>
        <div class="brand-sub">Top 200 Digital Assets &bull; Technical Momentum &bull; AI Market Insights</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- ENVIRONMENT VALIDATION ---
REQUIRED_ENV_VARS = [
    "DATABRICKS_SERVER_HOSTNAME",
    "DATABRICKS_HTTP_PATH",
    "DATABRICKS_TOKEN",
    "GROQ_API_KEY",
]
missing_vars = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
if missing_vars:
    st.error(f"Missing required environment variables in .env: {', '.join(missing_vars)}")
    st.stop()


# --- 1. DATABASE CONNECTION & DATA LOADER ---
@st.cache_resource
def get_db_connection():
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
    )


@st.cache_data(ttl=300, show_spinner="Loading market data...")
def load_market_data() -> pd.DataFrame:
    conn = get_db_connection()
    query = """
        SELECT
            f.coin_id,
            f.symbol,
            d.name,
            d.market_cap_rank,
            f.market_date,
            f.price_usd,
            f.prev_price_usd,
            f.price_change_24h_pct,
            f.market_cap,
            f.total_volume,
            f.sma_7d_price,
            f.volatility_7d,
            f.volume_to_mcap_ratio,
            f.trend_signal
        FROM crypto_project.crypto.fact_crypto_daily f
        JOIN crypto_project.crypto.dim_coins d
            ON f.coin_id = d.coin_id
        ORDER BY f.market_date DESC, d.market_cap_rank ASC
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    df_out = pd.DataFrame(rows, columns=columns)
    numeric_cols = [
        "market_cap_rank",
        "price_usd",
        "prev_price_usd",
        "price_change_24h_pct",
        "market_cap",
        "total_volume",
        "sma_7d_price",
        "volatility_7d",
        "volume_to_mcap_ratio",
    ]
    for col in numeric_cols:
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce")
    return df_out


# --- 2. TOKEN-OPTIMIZED DETERMINISTIC GROQ ENGINE ---
def format_compact_table(df_subset: pd.DataFrame) -> str:
    header = "Rank|Symbol|Name|PriceUSD|24hPct|7DSMA|Vol7D|VolToMcap|McapB|Trend"
    lines = [header]
    for _, r in df_subset.iterrows():
        mcap_b = (r["market_cap"] / 1e9) if pd.notna(r["market_cap"]) else 0.0
        sma = f"{r['sma_7d_price']:.4f}" if pd.notna(r["sma_7d_price"]) else "NA"
        vol = f"{r['volatility_7d']:.4f}" if pd.notna(r["volatility_7d"]) else "NA"
        v_ratio = f"{r['volume_to_mcap_ratio']:.4f}" if pd.notna(r["volume_to_mcap_ratio"]) else "NA"
        chg = f"{r['price_change_24h_pct']:+.2f}" if pd.notna(r["price_change_24h_pct"]) else "0.00"
        lines.append(
            f"{int(r['market_cap_rank'])}|{r['symbol']}|{r['name']}|"
            f"{r['price_usd']:.4f}|{chg}|{sma}|{vol}|{v_ratio}|{mcap_b:.2f}|{r['trend_signal']}"
        )
    return "\n".join(lines)


def build_compact_context(df_day: pd.DataFrame, user_question: str = "") -> str:
    total_coins = len(df_day)
    above_sma = int((df_day["trend_signal"] == "ABOVE_7D_SMA").sum())
    below_sma = int((df_day["trend_signal"] == "BELOW_7D_SMA").sum())
    total_mcap_b = df_day["market_cap"].sum() / 1e9
    total_vol_b = df_day["total_volume"].sum() / 1e9

    matched_df = pd.DataFrame()
    if user_question:
        tokens = set(re.findall(r"[A-Za-z0-9]{2,15}", user_question.upper()))
        q_lower = user_question.lower()
        mask = df_day["symbol"].str.upper().isin(tokens) | df_day["name"].str.lower().apply(
            lambda n: n in q_lower
        )
        matched_df = df_day[mask]

    top20 = df_day.head(20)
    top5_gainers = df_day.sort_values("price_change_24h_pct", ascending=False).head(5)
    top5_losers = df_day.sort_values("price_change_24h_pct", ascending=True).head(5)
    top5_vol_ratio = df_day.sort_values("volume_to_mcap_ratio", ascending=False).head(5)

    combined = (
        pd.concat([matched_df, top20, top5_gainers, top5_losers, top5_vol_ratio], ignore_index=True)
        .drop_duplicates(subset=["coin_id"])
        .sort_values("market_cap_rank")
    )

    breadth_block = (
        f"DATE: {df_day['market_date'].max()}\n"
        f"MARKET_BREADTH: Total={total_coins}, Above_7D_SMA={above_sma} ({(above_sma/total_coins)*100:.1f}%), "
        f"Below_7D_SMA={below_sma}, Total_Mcap=${total_mcap_b:.2f}B, Total_24h_Vol=${total_vol_b:.2f}B\n"
    )
    return breadth_block + "\nASSETS (Pipe-Delimited):\n" + format_compact_table(combined)


def call_groq_deterministic(system_prompt: str, user_prompt: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    last_err = None

    for model_id in ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                top_p=1.0,
                seed=42,
                max_tokens=2048,
                reasoning_effort="low",
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception as err:
            last_err = err
    raise RuntimeError(f"Groq API call failed across models: {last_err}")


@st.cache_data(ttl=3600, show_spinner=False)
def generate_deterministic_outlook(data_hash: str, compact_context: str) -> dict:
    system_prompt = (
        "You are a Senior Quantitative Crypto Strategist. Rely EXCLUSIVELY on the provided market metrics. "
        "Never invent external news. Compute market regime objectively from breadth (Above_7D_SMA %), large-cap momentum "
        "(BTC, ETH, SOL), and VolToMcap liquidity ratios. Respond with ONLY a raw JSON object—no markdown, no backticks, no prose."
    )
    user_prompt = f"""
{compact_context}

Output ONLY this exact raw JSON object:
{{
    "market_bias": "BULLISH",
    "confidence_score": 0.80,
    "strongest_coin": "SYMBOL",
    "weakest_coin": "SYMBOL",
    "executive_summary": "3 concise sentences citing exact prices, 7D SMA alignment, and breadth %.",
    "risk_factor": "1 short sentence identifying the primary volatility or concentration risk."
}}
"""
    raw = call_groq_deterministic(system_prompt, user_prompt)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Model did not return valid JSON: {raw[:200]}")
    return json.loads(match.group(0))


@st.cache_data(ttl=3600, show_spinner=False)
def ask_groq_analyst(data_hash: str, user_question: str, compact_context: str) -> str:
    system_prompt = (
        "You are a Quantitative Crypto Market Analyst. "
        "Answer ONLY using exact numbers and columns in the provided market data. "
        "If an asset is not listed in the provided data, state plainly that it was not matched in the Top 200 dataset. "
        "Format your answer cleanly with short bullet points and a 1-sentence conclusion."
    )
    user_prompt = f"""
{compact_context}

USER QUESTION:
{user_question.strip()}
"""
    return call_groq_deterministic(system_prompt, user_prompt)


# --- 3. ANIMATED SVG CHART COMPONENTS ---
def render_animated_bar_chart(df_perf: pd.DataFrame, is_gainer: bool):
    accent = "#00E599" if is_gainer else "#F85149"
    accent_glow = "rgba(0, 229, 153, 0.35)" if is_gainer else "rgba(248, 81, 73, 0.35)"
    grad_top = "#00E599" if is_gainer else "#FF7B72"
    grad_bot = "#059669" if is_gainer else "#B91C1C"

    max_abs = max(df_perf["price_change_24h_pct"].abs().max(), 1.0)
    bars_html = ""
    for idx, (_, row) in enumerate(df_perf.iterrows()):
        val = float(row["price_change_24h_pct"])
        pct_height = max(int((abs(val) / max_abs) * 175), 14)
        delay = idx * 0.1
        bars_html += f"""
        <div class="bar-col">
            <div class="bar-val" style="color:{accent};">{val:+.2f}%</div>
            <div class="bar-track">
                <div class="bar-fill" style="
                    height:{pct_height}px;
                    background: linear-gradient(180deg, {grad_top} 0%, {grad_bot} 100%);
                    box-shadow: 0 0 18px {accent_glow};
                    animation-delay: {delay}s;
                "></div>
            </div>
            <div class="bar-sym">{row['symbol']}</div>
            <div class="bar-price">${row['price_usd']:,.2f}</div>
        </div>
        """

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #F0F6FC;
        }}
        .chart-card {{
            background: rgba(13, 17, 23, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 18px 16px 14px 16px;
            height: 278px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
        }}
        .bars-wrap {{
            display: flex;
            justify-content: space-around;
            align-items: flex-end;
            height: 235px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 8px;
        }}
        .bar-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 18%;
        }}
        .bar-val {{
            font-size: 12px;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            margin-bottom: 6px;
        }}
        .bar-track {{
            width: 38px;
            height: 180px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px 8px 4px 4px;
            display: flex;
            align-items: flex-end;
            overflow: hidden;
        }}
        @keyframes riseUp {{
            from {{ transform: scaleY(0); opacity: 0.2; }}
            to   {{ transform: scaleY(1); opacity: 1; }}
        }}
        .bar-fill {{
            width: 100%;
            border-radius: 8px 8px 4px 4px;
            transform-origin: bottom;
            animation: riseUp 0.75s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }}
        .bar-sym {{
            margin-top: 8px;
            font-size: 13px;
            font-weight: 700;
            color: #F0F6FC;
        }}
        .bar-price {{
            font-size: 11px;
            color: #8B949E;
            font-variant-numeric: tabular-nums;
        }}
    </style>
    </head>
    <body>
        <div class="chart-card">
            <div class="bars-wrap">{bars_html}</div>
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=286)


def render_animated_spline_chart(df_coin: pd.DataFrame, symbol: str):
    df_c = df_coin.sort_values("market_date").tail(14).reset_index(drop=True)
    n = len(df_c)
    latest_p = float(df_c["price_usd"].iloc[-1])
    latest_sma = float(df_c["sma_7d_price"].iloc[-1]) if pd.notna(df_c["sma_7d_price"].iloc[-1]) else latest_p
    diff_pct = ((latest_p - latest_sma) / latest_sma * 100) if latest_sma else 0.0

    w, h = 560, 195
    pad_x, pad_y = 26, 22

    if n == 1:
        y_mid = h // 2
        price_path = f"M {pad_x},{y_mid - 14} L {w - pad_x},{y_mid - 14}"
        sma_path = f"M {pad_x},{y_mid + 16} L {w - pad_x},{y_mid + 16}"
        area_path = f"{price_path} L {w - pad_x},{h - pad_y} L {pad_x},{h - pad_y} Z"
        dots_svg = f'<circle cx="{w//2}" cy="{y_mid - 14}" r="5" fill="#00E599" />'
        date_labels = f'<text x="{pad_x}" y="{h - 4}" fill="#8B949E" font-size="11">{df_c["market_date"].iloc[0]}</text>'
    else:
        all_vals = pd.concat([df_c["price_usd"], df_c["sma_7d_price"].fillna(df_c["price_usd"])])
        v_min, v_max = float(all_vals.min()), float(all_vals.max())
        span = max(v_max - v_min, v_max * 0.01, 1e-6)

        def to_xy(i, val):
            x = pad_x + (i / (n - 1)) * (w - 2 * pad_x)
            y = (h - pad_y - 14) - ((float(val) - v_min) / span) * (h - 2 * pad_y - 20)
            return round(x, 1), round(y, 1)

        p_pts = [to_xy(i, df_c["price_usd"].iloc[i]) for i in range(n)]
        s_pts = [
            to_xy(i, df_c["sma_7d_price"].iloc[i] if pd.notna(df_c["sma_7d_price"].iloc[i]) else df_c["price_usd"].iloc[i])
            for i in range(n)
        ]

        price_path = "M " + " L ".join(f"{x},{y}" for x, y in p_pts)
        sma_path = "M " + " L ".join(f"{x},{y}" for x, y in s_pts)
        area_path = f"{price_path} L {p_pts[-1][0]},{h - pad_y} L {p_pts[0][0]},{h - pad_y} Z"
        dots_svg = "".join(
            f'<circle cx="{x}" cy="{y}" r="3.5" fill="#00E599" stroke="#05070A" stroke-width="1.5" />'
            for x, y in p_pts
        )
        date_labels = (
            f'<text x="{pad_x}" y="{h - 4}" fill="#8B949E" font-size="11">{df_c["market_date"].iloc[0]}</text>'
            f'<text x="{w - pad_x}" y="{h - 4}" fill="#8B949E" font-size="11" text-anchor="end">{df_c["market_date"].iloc[-1]}</text>'
        )

    badge_color = "#00E599" if diff_pct >= 0 else "#F85149"
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #F0F6FC;
        }}
        .card {{
            background: rgba(13, 17, 23, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 14px 16px;
            height: 278px;
            box-sizing: border-box;
        }}
        .top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .coin-stat {{
            font-size: 13px;
            color: #C9D1D9;
            font-variant-numeric: tabular-nums;
        }}
        .legend {{
            font-size: 11px;
            color: #8B949E;
        }}
        @keyframes drawLine {{
            from {{ stroke-dashoffset: 1200; }}
            to   {{ stroke-dashoffset: 0; }}
        }}
        .anim-line {{
            stroke-dasharray: 1200;
            stroke-dashoffset: 1200;
            animation: drawLine 1.3s ease-out forwards;
        }}
    </style>
    </head>
    <body>
        <div class="card">
            <div class="top-row">
                <div class="coin-stat">
                    <strong>{symbol}</strong>: ${latest_p:,.4f} &nbsp;|&nbsp; 7D SMA: ${latest_sma:,.4f}
                    <span style="color:{badge_color}; font-weight:700;">({diff_pct:+.2f}% vs SMA)</span>
                </div>
                <div class="legend">
                    <span style="color:#00E599;">&#9644; Price</span> &nbsp;
                    <span style="color:#388BFD;">&#9644; 7D SMA</span>
                </div>
            </div>
            <svg viewBox="0 0 {w} {h}" width="100%" height="220">
                <defs>
                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#00E599" stop-opacity="0.28" />
                        <stop offset="100%" stop-color="#00E599" stop-opacity="0.0" />
                    </linearGradient>
                </defs>
                <line x1="{pad_x}" y1="40" x2="{w - pad_x}" y2="40" stroke="rgba(255,255,255,0.05)" />
                <line x1="{pad_x}" y1="100" x2="{w - pad_x}" y2="100" stroke="rgba(255,255,255,0.05)" />
                <line x1="{pad_x}" y1="160" x2="{w - pad_x}" y2="160" stroke="rgba(255,255,255,0.05)" />
                <path d="{area_path}" fill="url(#areaGrad)" />
                <path d="{sma_path}" fill="none" stroke="#388BFD" stroke-width="2" stroke-dasharray="5,4" />
                <path d="{price_path}" fill="none" stroke="#00E599" stroke-width="2.8" class="anim-line" />
                {dots_svg}
                {date_labels}
            </svg>
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=286)


def render_breadth_gauge_and_donut(df_day: pd.DataFrame):
    total = len(df_day)
    above = int((df_day["trend_signal"] == "ABOVE_7D_SMA").sum())
    breadth_pct = round((above / total) * 100, 1) if total else 0.0

    arc_len = 251.2
    filled_len = round((breadth_pct / 100.0) * arc_len, 1)
    regime_label = "BULLISH REGIME" if breadth_pct >= 55 else "BEARISH REGIME" if breadth_pct <= 40 else "NEUTRAL / MIXED"
    regime_color = "#00E599" if breadth_pct >= 55 else "#F85149" if breadth_pct <= 40 else "#FBBF24"

    top10_mcap = float(df_day[df_day["market_cap_rank"] <= 10]["market_cap"].sum())
    mid40_mcap = float(df_day[(df_day["market_cap_rank"] > 10) & (df_day["market_cap_rank"] <= 50)]["market_cap"].sum())
    rest_mcap = float(df_day[df_day["market_cap_rank"] > 50]["market_cap"].sum())
    mcap_sum = max(top10_mcap + mid40_mcap + rest_mcap, 1.0)

    p1 = round((top10_mcap / mcap_sum) * 100, 1)
    p2 = round((mid40_mcap / mcap_sum) * 100, 1)
    p3 = round(max(100.0 - p1 - p2, 0.0), 1)

    circ = 282.7
    d1 = round((p1 / 100.0) * circ, 1)
    d2 = round((p2 / 100.0) * circ, 1)
    d3 = round((p3 / 100.0) * circ, 1)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #F0F6FC;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
        }}
        .glass-box {{
            background: rgba(13, 17, 23, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 16px 20px;
            height: 215px;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .box-title {{
            font-size: 13px;
            font-weight: 600;
            color: #8B949E;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }}
        .big-stat {{
            font-size: 28px;
            font-weight: 800;
            color: #FFFFFF;
            font-variant-numeric: tabular-nums;
        }}
        .sub-stat {{
            font-size: 12px;
            margin-top: 6px;
            font-weight: 600;
        }}
        .legend-item {{
            font-size: 12px;
            color: #C9D1D9;
            margin-bottom: 7px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}
        @keyframes sweepArc {{
            from {{ stroke-dasharray: 0 300; }}
        }}
        .anim-arc {{
            animation: sweepArc 1.1s ease-out forwards;
        }}
    </style>
    </head>
    <body>
        <div class="grid">
            <div class="glass-box">
                <div>
                    <div class="box-title">7D SMA Bullish Breadth Gauge</div>
                    <div class="big-stat">{breadth_pct}%</div>
                    <div class="sub-stat" style="color:{regime_color};">&#9679; {regime_label} ({above}/{total} Coins)</div>
                </div>
                <svg width="190" height="120" viewBox="0 0 200 120">
                    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="16" stroke-linecap="round" />
                    <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="{regime_color}" stroke-width="16" stroke-linecap="round"
                          stroke-dasharray="{filled_len} {arc_len}" class="anim-arc" />
                    <text x="100" y="94" text-anchor="middle" fill="#F0F6FC" font-size="16" font-weight="700">{above} / {total}</text>
                </svg>
            </div>

            <div class="glass-box">
                <div>
                    <div class="box-title">Market Cap Tier Concentration</div>
                    <div class="legend-item"><span class="dot" style="background:#00E599;"></span>Top 10 Large Caps: <strong>{p1}%</strong></div>
                    <div class="legend-item"><span class="dot" style="background:#388BFD;"></span>Rank 11–50 Mid Caps: <strong>{p2}%</strong></div>
                    <div class="legend-item"><span class="dot" style="background:#A855F7;"></span>Rank 51–200 Altcoins: <strong>{p3}%</strong></div>
                </div>
                <svg width="135" height="135" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="45" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="14" />
                    <circle cx="60" cy="60" r="45" fill="none" stroke="#00E599" stroke-width="14"
                            stroke-dasharray="{d1} {circ}" transform="rotate(-90 60 60)" class="anim-arc" />
                    <circle cx="60" cy="60" r="45" fill="none" stroke="#388BFD" stroke-width="14"
                            stroke-dasharray="{d2} {circ}" stroke-dashoffset="-{d1}" transform="rotate(-90 60 60)" />
                    <circle cx="60" cy="60" r="45" fill="none" stroke="#A855F7" stroke-width="14"
                            stroke-dasharray="{d3} {circ}" stroke-dashoffset="-{round(d1 + d2, 1)}" transform="rotate(-90 60 60)" />
                    <text x="60" y="64" text-anchor="middle" fill="#F0F6FC" font-size="12" font-weight="700">TOP 200</text>
                </svg>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=225)


# --- LOAD DATA ---
df = load_market_data()

if df.empty:
    st.warning("No market records available.")
    st.stop()

latest_date = df["market_date"].max()
df_latest = df[df["market_date"] == latest_date].sort_values("market_cap_rank").reset_index(drop=True)

base_context = build_compact_context(df_latest)
data_hash = hashlib.sha256(base_context.encode("utf-8")).hexdigest()

# --- COMPUTE 8 EXECUTIVE KPIS ---
total_mcap_b = df_latest["market_cap"].sum() / 1e9
total_vol_b = df_latest["total_volume"].sum() / 1e9
btc_row = df_latest[df_latest["symbol"] == "BTC"]
btc_dom_pct = (float(btc_row["market_cap"].iloc[0]) / df_latest["market_cap"].sum() * 100) if not btc_row.empty else 0.0
above_sma_count = int((df_latest["trend_signal"] == "ABOVE_7D_SMA").sum())
breadth_pct = (above_sma_count / len(df_latest)) * 100

top_gainer = df_latest.loc[df_latest["price_change_24h_pct"].idxmax()]
top_loser = df_latest.loc[df_latest["price_change_24h_pct"].idxmin()]
median_chg = float(df_latest["price_change_24h_pct"].median())
liq_leader = df_latest.loc[df_latest["volume_to_mcap_ratio"].idxmax()]

# --- ROW 1: 4 GRADIENT HERO KPI CARDS ---
h1, h2, h3, h4 = st.columns(4, gap="medium")
with h1:
    st.markdown(
        f"""
        <div class="hero-kpi hero-grad-emerald">
            <div class="hero-kpi-label">Top 200 Market Cap</div>
            <div class="hero-kpi-val">${total_mcap_b:,.1f}B</div>
            <div class="hero-kpi-sub">As of {latest_date}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h2:
    st.markdown(
        f"""
        <div class="hero-kpi hero-grad-indigo">
            <div class="hero-kpi-label">24h Global Volume</div>
            <div class="hero-kpi-val">${total_vol_b:,.1f}B</div>
            <div class="hero-kpi-sub">Turnover: {(total_vol_b / total_mcap_b) * 100:.2f}% of Mcap</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h3:
    st.markdown(
        f"""
        <div class="hero-kpi hero-grad-cyan">
            <div class="hero-kpi-label">BTC Dominance (Top 200)</div>
            <div class="hero-kpi-val">{btc_dom_pct:.2f}%</div>
            <div class="hero-kpi-sub">BTC Price: ${float(btc_row['price_usd'].iloc[0]):,.0f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h4:
    st.markdown(
        f"""
        <div class="hero-kpi hero-grad-amber">
            <div class="hero-kpi-label">7D SMA Bullish Breadth</div>
            <div class="hero-kpi-val">{breadth_pct:.1f}%</div>
            <div class="hero-kpi-sub">{above_sma_count} of {len(df_latest)} Above 7D SMA</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# --- ROW 2: 4 UNIFORM GLASS TERMINAL KPI CARDS ---
k1, k2, k3, k4 = st.columns(4, gap="medium")
k1.metric(
    "24h Top Gainer",
    f"{top_gainer['symbol']} (${top_gainer['price_usd']:,.2f})",
    delta=f"{top_gainer['price_change_24h_pct']:+.2f}%",
)
k2.metric(
    "24h Top Loser",
    f"{top_loser['symbol']} (${top_loser['price_usd']:,.2f})",
    delta=f"{top_loser['price_change_24h_pct']:+.2f}%",
)
k3.metric(
    "Median 24h Return",
    f"{median_chg:+.2f}%",
    delta="Top 200 Benchmark",
    delta_color="normal" if median_chg >= 0 else "inverse",
)
k4.metric(
    "Highest Liquidity Ratio",
    f"{liq_leader['symbol']} ({liq_leader['volume_to_mcap_ratio']:.2f}x)",
    delta="24h Volume / Market Cap",
    delta_color="off",
)

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# --- ROW 3: RADIAL BREADTH GAUGE + MARKET CAP TIER DONUT ---
render_breadth_gauge_and_donut(df_latest)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- ROW 4: ANIMATED CHARTS (TOP 5 PERFORMERS + PRICE VS 7D SMA SPLINE) ---
chart_left, chart_right = st.columns(2, gap="large")

with chart_left:
    st.markdown(
        '<div class="glass-panel-title"><span>Top 5 Performers (24h Return %)</span><span class="panel-tag">24H MOVERS</span></div>',
        unsafe_allow_html=True,
    )
    perf_view = st.selectbox(
        "Performance Ranking",
        options=["Top 5 Gainers (24h %)", "Top 5 Losers (24h %)"],
        index=0,
        label_visibility="collapsed",
    )
    is_gainer_view = perf_view.startswith("Top 5 Gainers")
    df_perf = (
        df_latest.dropna(subset=["price_change_24h_pct"])
        .sort_values("price_change_24h_pct", ascending=not is_gainer_view)
        .head(5)
    )
    render_animated_bar_chart(df_perf, is_gainer=is_gainer_view)

with chart_right:
    st.markdown(
        '<div class="glass-panel-title"><span>Price vs. 7-Day Rolling SMA</span><span class="panel-tag">TREND LINE</span></div>',
        unsafe_allow_html=True,
    )
    coin_options = df_latest["symbol"].tolist()
    selected_symbol = st.selectbox(
        "Select Asset",
        options=coin_options,
        index=0,
        label_visibility="collapsed",
    )
    df_coin = df[df["symbol"] == selected_symbol]
    render_animated_spline_chart(df_coin, selected_symbol)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# --- ROW 5: AI QUANTITATIVE OUTLOOK + DIRECT AI ANALYST PANEL ---
ai_left, ai_right = st.columns(2, gap="large")

with ai_left:
    st.markdown(
        '<div class="glass-panel-title"><span>AI Market Regime Outlook</span><span class="panel-tag">QUANT BRIEF</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("Generate Quantitative Market Brief", type="primary", use_container_width=True):
        st.session_state["show_outlook"] = True

    if st.session_state.get("show_outlook", False):
        with st.spinner("Analyzing market breadth and momentum..."):
            ai_out = generate_deterministic_outlook(data_hash, base_context)

        bias = ai_out["market_bias"].upper()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Market Bias", bias, delta="Regime", delta_color="off")
        m2.metric("Confidence", f"{int(ai_out['confidence_score'] * 100)}%", delta="Score", delta_color="off")
        m3.metric("Leader", ai_out["strongest_coin"], delta="Top Momentum", delta_color="off")
        m4.metric("Laggard", ai_out["weakest_coin"], delta="Weakest", delta_color="off")

        st.markdown(
            f"""
            <div class="ai-brief-card">
                <strong>Quantitative Brief:</strong> {ai_out['executive_summary']}
                <div class="ai-risk-banner"><strong>Risk Note:</strong> {ai_out['risk_factor']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("Click **Generate Quantitative Market Brief** to evaluate market breadth, 7D SMA alignment, and liquidity ratios.")

with ai_right:
    st.markdown(
        '<div class="glass-panel-title"><span>Ask AI Market Analyst</span><span class="panel-tag">INTERACTIVE Q&A</span></div>',
        unsafe_allow_html=True,
    )
    with st.form(key="groq_qa_form", clear_on_submit=False):
        user_query = st.text_input(
            "Ask a question about the market",
            placeholder="e.g. Compare BTC, ETH, and SOL on price, 7D SMA, and volume ratio...",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Ask AI Analyst", use_container_width=True)

    if submitted:
        if not user_query.strip():
            st.warning("Type a question about any coin or metric.")
        else:
            with st.spinner("Analyzing market metrics..."):
                targeted_context = build_compact_context(df_latest, user_query)
                answer = ask_groq_analyst(data_hash, user_query, targeted_context)
                st.session_state["last_groq_q"] = user_query.strip()
                st.session_state["last_groq_a"] = answer

    if "last_groq_a" in st.session_state:
        st.markdown(
            f"""
            <div class="ai-brief-card">
                <div style="color:#8B949E; font-size:0.82rem; margin-bottom:6px;">
                    <strong>Query:</strong> {st.session_state['last_groq_q']}
                </div>
                {st.session_state['last_groq_a']}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("Ask about any Top 200 coin (e.g., *'Which coins have the highest volume-to-market-cap ratio?'* or *'Analyze SOL vs 7D SMA'*).")

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# --- ROW 6: SEARCHABLE MARKET EXPLORER TABLE ---
st.markdown(
    f'<div class="glass-panel-title"><span>Top 200 Market Explorer ({latest_date})</span><span class="panel-tag">LIVE METRICS</span></div>',
    unsafe_allow_html=True,
)

f1, f2 = st.columns([2, 1], gap="medium")
with f1:
    trend_filter = st.multiselect(
        "Filter by 7D SMA Trend Signal",
        options=["ABOVE_7D_SMA", "BELOW_7D_SMA", "NEUTRAL"],
        default=["ABOVE_7D_SMA", "BELOW_7D_SMA", "NEUTRAL"],
    )
with f2:
    search_term = st.text_input("Search Coin Symbol or Name", placeholder="e.g. BTC, Ethereum, SOL...").strip().lower()

filtered_df = df_latest[df_latest["trend_signal"].isin(trend_filter)].copy()
if search_term:
    filtered_df = filtered_df[
        filtered_df["symbol"].str.lower().str.contains(search_term)
        | filtered_df["name"].str.lower().str.contains(search_term)
    ]

display_cols = [
    "market_cap_rank",
    "symbol",
    "name",
    "price_usd",
    "price_change_24h_pct",
    "sma_7d_price",
    "volatility_7d",
    "volume_to_mcap_ratio",
    "market_cap",
    "total_volume",
    "trend_signal",
]


def style_pct(val):
    if pd.isna(val):
        return ""
    if val > 0:
        return "color: #00E599; font-weight: 600;"
    if val < 0:
        return "color: #F85149; font-weight: 600;"
    return "color: #8B949E;"


def style_signal(val):
    if val == "ABOVE_7D_SMA":
        return "background-color: rgba(0, 229, 153, 0.12); color: #00E599; font-weight: 600;"
    if val == "BELOW_7D_SMA":
        return "background-color: rgba(248, 81, 73, 0.12); color: #F85149; font-weight: 600;"
    return "color: #8B949E;"


styled_df = (
    filtered_df[display_cols]
    .style.map(style_pct, subset=["price_change_24h_pct"])
    .map(style_signal, subset=["trend_signal"])
    .format(
        {
            "price_usd": "${:,.4f}",
            "price_change_24h_pct": "{:+.2f}%",
            "sma_7d_price": "${:,.4f}",
            "volatility_7d": "{:,.4f}",
            "volume_to_mcap_ratio": "{:.4f}",
            "market_cap": "${:,.0f}",
            "total_volume": "${:,.0f}",
        },
        na_rep="—",
    )
)

st.dataframe(styled_df, use_container_width=True, hide_index=True, height=460)