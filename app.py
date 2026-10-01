"""
NIFTY 50 Market Risk Engine — Backend Server
9 Global Instruments to 50 Companies Early-Warning Intelligence System
"""
import os
import json
import math
import random
from datetime import datetime, timedelta, timezone
from collections import defaultdict, OrderedDict

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ---------------------------------------------------------------------------
# CONSTANTS — 50 NIFTY Companies with sectors & character profiles
# ---------------------------------------------------------------------------
NIFTY_50_COMPANIES = [
    ("RELIANCE", "Reliance Industries Ltd", "Oil & Gas"),
    ("HDFCBANK", "HDFC Bank Ltd", "Financial Services"),
    ("ICICIBANK", "ICICI Bank Ltd", "Financial Services"),
    ("BHARTIARTL", "Bharti Airtel Ltd", "Telecom"),
    ("LT", "Larsen & Toubro Ltd", "Construction"),
    ("SBIN", "State Bank of India", "Financial Services"),
    ("INFY", "Infosys Ltd", "Information Technology"),
    ("TCS", "Tata Consultancy Services Ltd", "Information Technology"),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "Financial Services"),
    ("HINDUNILVR", "Hindustan Unilever Ltd", "FMCG"),
    ("ITC", "ITC Ltd", "FMCG"),
    ("BAJFINANCE", "Bajaj Finance Ltd", "Financial Services"),
    ("MARUTI", "Maruti Suzuki India Ltd", "Automobile"),
    ("TITAN", "Titan Company Ltd", "Consumer Durables"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd", "Pharma"),
    ("HCLTECH", "HCL Technologies Ltd", "Information Technology"),
    ("AXISBANK", "Axis Bank Ltd", "Financial Services"),
    ("NTPC", "NTPC Ltd", "Power"),
    ("ONGC", "Oil and Natural Gas Corporation Ltd", "Oil & Gas"),
    ("M&M", "Mahindra & Mahindra Ltd", "Automobile"),
    ("WIPRO", "Wipro Ltd", "Information Technology"),
    ("ULTRACEMCO", "UltraTech Cement Ltd", "Cement"),
    ("BAJAJFINSV", "Bajaj Finserv Ltd", "Financial Services"),
    ("TATASTEEL", "Tata Steel Ltd", "Metals & Mining"),
    ("POWERGRID", "Power Grid Corporation of India Ltd", "Power"),
    ("ASIANPAINT", "Asian Paints Ltd", "Consumer Durables"),
    ("NESTLEIND", "Nestle India Ltd", "FMCG"),
    ("HDFCLIFE", "HDFC Life Insurance Company Ltd", "Financial Services"),
    ("JSWSTEEL", "JSW Steel Ltd", "Metals & Mining"),
    ("TECHM", "Tech Mahindra Ltd", "Information Technology"),
    ("ADANIPORTS", "Adani Ports and SEZ Ltd", "Services"),
    ("SBILIFE", "SBI Life Insurance Company Ltd", "Financial Services"),
    ("COALINDIA", "Coal India Ltd", "Metals & Mining"),
    ("TATAMOTORS", "Tata Motors Ltd", "Automobile"),
    ("BAJAJ-AUTO", "Bajaj Auto Ltd", "Automobile"),
    ("BRITANNIA", "Britannia Industries Ltd", "FMCG"),
    ("MARICO", "Marico Ltd", "FMCG"),
    ("DIVISLAB", "Divi's Laboratories Ltd", "Pharma"),
    ("DRREDDY", "Dr. Reddy's Laboratories Ltd", "Pharma"),
    ("HINDALCO", "Hindalco Industries Ltd", "Metals & Mining"),
    ("ADANIENT", "Adani Enterprises Ltd", "Metals & Mining"),
    ("APOLLOHOSP", "Apollo Hospitals Enterprise Ltd", "Healthcare"),
    ("CIPLA", "Cipla Ltd", "Pharma"),
    ("TRENT", "Trent Ltd", "Consumer Durables"),
    ("BEL", "Bharat Electronics Ltd", "Capital Goods"),
    ("GRASIM", "Grasim Industries Ltd", "Cement"),
    ("EICHERMOT", "Eicher Motors Ltd", "Automobile"),
    ("BPCL", "Bharat Petroleum Corporation Ltd", "Oil & Gas"),
    ("INDUSINDBK", "IndusInd Bank Ltd", "Financial Services"),
    ("HEROMOTOCO", "Hero MotoCorp Ltd", "Automobile"),
]

SECTORS = sorted(set(s for _, _, s in NIFTY_50_COMPANIES))

# 9 Global Instruments
GLOBAL_INSTRUMENTS = [
    ("NIFTY50", "NIFTY 50 Index", "Equity Index"),
    ("CRUDEOIL", "Crude Oil (WTI)", "Commodity"),
    ("NATGAS", "Natural Gas (HH)", "Commodity"),
    ("GOLD", "Gold (XAU/USD)", "Precious Metal"),
    ("SILVER", "Silver (XAG/USD)", "Precious Metal"),
    ("COPPER", "Copper (HG)", "Base Metal"),
    ("ALUMINIUM", "Aluminium (LMAH)", "Base Metal"),
    ("ZINC", "Zinc (LMSZ)", "Base Metal"),
    ("ELECTRICITY", "Electricity (PJM)", "Energy"),
]

# ---------------------------------------------------------------------------
# Company Character Model — dynamic profiles
# ---------------------------------------------------------------------------
def _build_company_profiles():
    profiles = {}
    for sym, name, sector in NIFTY_50_COMPANIES:
        base = {
            "currency_sensitivity": random.uniform(-0.4, 0.4),
            "interest_rate_sensitivity": random.uniform(-0.5, 0.5),
            "volatility_character": random.choice(["Low", "Moderate", "High"]),
            "lead_lag": random.choice(["Direct", "Short-Lag", "Medium-Lag", "Long-Lag"]),
            "supply_chain_dependency": random.uniform(0.0, 1.0),
            "regulatory_exposure": random.uniform(0.0, 1.0),
        }
        # Sector-based defaults
        if sector == "Financial Services":
            base["interest_rate_sensitivity"] = random.uniform(0.6, 1.0)
            base["currency_sensitivity"] = random.uniform(-0.2, 0.2)
            base["lead_lag"] = "Direct"
        elif sector == "Information Technology":
            base["currency_sensitivity"] = random.uniform(0.5, 0.9)
            base["interest_rate_sensitivity"] = random.uniform(-0.3, 0.1)
            base["lead_lag"] = "Direct"
        elif sector in ("Oil & Gas",):
            base["interest_rate_sensitivity"] = random.uniform(-0.3, 0.1)
            base["lead_lag"] = "Short-Lag"
        elif sector in ("Metals & Mining", "Cement"):
            base["lead_lag"] = "Medium-Lag"
            base["supply_chain_dependency"] = random.uniform(0.5, 1.0)
        elif sector == "Pharma":
            base["lead_lag"] = "Medium-Lag"
            base["currency_sensitivity"] = random.uniform(0.3, 0.7)

        # Commodity exposure per instrument
        commodity_exp = {}
        for instr_sym, _, instr_type in GLOBAL_INSTRUMENTS:
            if instr_type == "Equity Index":
                commodity_exp[instr_sym] = random.uniform(0.3, 0.9)
            elif instr_type == "Commodity" and sector in ("Oil & Gas",):
                commodity_exp[instr_sym] = random.uniform(0.5, 1.0)
            elif instr_type == "Precious Metal":
                commodity_exp[instr_sym] = random.uniform(-0.2, 0.2)
            elif instr_type == "Base Metal" and sector in ("Metals & Mining", "Cement", "Capital Goods", "Construction"):
                commodity_exp[instr_sym] = random.uniform(0.4, 0.9)
            elif instr_type == "Energy" and sector in ("Power", "Oil & Gas"):
                commodity_exp[instr_sym] = random.uniform(0.4, 0.8)
            else:
                commodity_exp[instr_sym] = random.uniform(-0.2, 0.3)

        base["commodity_exposure"] = commodity_exp
        profiles[sym] = base
    return profiles

COMPANY_PROFILES = _build_company_profiles()

# ---------------------------------------------------------------------------
# Instrument price simulator
# ---------------------------------------------------------------------------
_instrument_prices = {}

def _init_prices():
    base_prices = {
        "NIFTY50": 24500.0, "CRUDEOIL": 78.5, "NATGAS": 2.8,
        "GOLD": 2350.0, "SILVER": 28.5, "COPPER": 4.2,
        "ALUMINIUM": 2600.0, "ZINC": 2800.0, "ELECTRICITY": 45.0,
    }
    for k, v in base_prices.items():
        _instrument_prices[k] = {"price": v, "change_pct": 0.0, "high": v, "low": v}
_init_prices()

def _tick_prices():
    now = datetime.now(timezone.utc)
    for sym in _instrument_prices:
        volatility = 0.002
        change = random.gauss(0, volatility)
        old = _instrument_prices[sym]["price"]
        new = old * (1 + change)
        _instrument_prices[sym] = {
            "price": round(new, 2),
            "change_pct": round(change * 100, 2),
            "high": max(_instrument_prices[sym]["high"], new),
            "low": min(_instrument_prices[sym]["low"], new),
            "timestamp": now.isoformat(),
        }

# ---------------------------------------------------------------------------
# Evidence Engine
# ---------------------------------------------------------------------------
class EvidenceEngine:
    def __init__(self):
        self.signals = []
        self._signal_id = 0

    def generate_signals(self):
        self._signal_id += 1
        new_signals = []
        _tick_prices()

        moved_instruments = [
            (sym, data) for sym, data in _instrument_prices.items()
            if abs(data["change_pct"]) > 0.15
        ]
        if not moved_instruments:
            return []

        for instr_sym, instr_data in moved_instruments[:2]:
            direction = "bullish" if instr_data["change_pct"] > 0 else "bearish"
            affected = []
            for company_sym, profile in COMPANY_PROFILES.items():
                exposure = profile["commodity_exposure"].get(instr_sym, 0)
                if abs(exposure) > 0.3:
                    affected.append((company_sym, exposure))
            if not affected:
                continue

            affected.sort(key=lambda x: abs(x[1]), reverse=True)
            top_companies = affected[:5]

            confidence = min(0.95, 0.5 + abs(instr_data["change_pct"]) * 0.5 + random.uniform(0, 0.2))
            impact_timing = self._estimate_timing(top_companies)

            signal = {
                "id": self._signal_id,
                "instrument": instr_sym,
                "direction": direction,
                "strength": round(abs(instr_data["change_pct"]), 2),
                "confidence": round(confidence, 2),
                "probability": round(random.uniform(0.4, 0.9), 2),
                "impact_timing": impact_timing,
                "affected_companies": [
                    {"symbol": c[0], "exposure": round(c[1], 2),
                     "expected_impact": direction if c[1] > 0 else ("bearish" if direction == "bullish" else "bullish")}
                    for c in top_companies
                ],
                "evidence": [
                    {"source": f"{instr_sym} Price Action", "type": "technical",
                     "detail": f"{instr_sym} moved {direction.upper()} by {abs(instr_data['change_pct']):.2f}%", "weight": "high"},
                    {"source": "Company Correlation Model", "type": "fundamental",
                     "detail": f"Top {len(top_companies)} correlated companies show consistent sensitivity", "weight": "medium"},
                ],
                "conflicting_evidence": [
                    {"source": "Sector Divergence", "detail": "Not all sectors confirming the move", "weight": "low"},
                    {"source": "Volume Profile", "detail": "Below-average volume suggests lack of conviction", "weight": "low"},
                ],
                "data_freshness": "live",
                "assumptions": ["Historical correlation patterns hold", "No regime change detected", "Liquidity conditions normal"],
                "risk_factors": ["Unexpected news event could override", "Low liquidity window approaching", "Month-end rebalancing possible"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "time_horizon": impact_timing,
            }
            new_signals.append(signal)

        self.signals.extend(new_signals)
        if len(self.signals) > 100:
            self.signals = self.signals[-100:]
        return new_signals

    def _estimate_timing(self, companies):
        timings = [COMPANY_PROFILES.get(c[0], {}).get("lead_lag", "Medium-Lag") for c in companies]
        if all(t == "Direct" for t in timings):
            return "Minutes / Hours"
        if any(t == "Direct" for t in timings):
            return "Same Day / 1 Day"
        if any(t == "Short-Lag" for t in timings):
            return "Same Day / 1 Day"
        return "Several Days"

    def get_active_signals(self, limit=20):
        return sorted(self.signals, key=lambda x: x["id"], reverse=True)[:limit]

evidence_engine = EvidenceEngine()

# ---------------------------------------------------------------------------
# Forward Intelligence Layer
# ---------------------------------------------------------------------------
def generate_forecasts():
    forecasts = []
    horizons = ["5 min", "15 min", "30 min", "60 min", "Next Session", "Next Day"]
    for instr_sym, instr_data in _instrument_prices.items():
        for horizon_label in horizons:
            base_prob = 0.5 + random.uniform(-0.15, 0.15)
            direction = random.choice(["bullish", "bearish", "neutral"])
            confidence = min(0.9, base_prob + random.uniform(-0.1, 0.2))
            price = instr_data.get("price", 100)
            offset = price * random.uniform(0.005, 0.02)
            if direction == "bullish":
                t_range = {"low": round(price + offset*0.5, 2), "high": round(price + offset, 2)}
            elif direction == "bearish":
                t_range = {"low": round(price - offset, 2), "high": round(price - offset*0.5, 2)}
            else:
                t_range = {"low": round(price*0.995, 2), "high": round(price*1.005, 2)}
            forecasts.append({
                "instrument": instr_sym, "horizon": horizon_label,
                "direction": direction, "probability": round(base_prob, 2),
                "confidence": round(confidence, 2), "target_range": t_range,
                "trigger_conditions": ["No unexpected macro event", "Current momentum persists", "Volume confirms direction"],
            })
    return forecasts

# ---------------------------------------------------------------------------
# Lead / Lag Model
# ---------------------------------------------------------------------------
def get_lead_lag_matrix():
    matrix = {}
    for instr_sym, instr_name, instr_type in GLOBAL_INSTRUMENTS:
        sector_timing = {}
        for sector in SECTORS:
            if instr_type == "Equity Index":
                sector_timing[sector] = "Direct"
            elif instr_type == "Commodity" and sector in ("Oil & Gas", "Metals & Mining"):
                sector_timing[sector] = "Short-Lag"
            elif instr_type == "Precious Metal":
                sector_timing[sector] = "Medium-Lag"
            elif instr_type == "Base Metal" and sector in ("Metals & Mining", "Cement", "Capital Goods"):
                sector_timing[sector] = "Short-Lag"
            elif instr_type == "Energy" and sector in ("Power", "Oil & Gas"):
                sector_timing[sector] = "Short-Lag"
            else:
                sector_timing[sector] = "Long-Lag"
        matrix[instr_sym] = {"name": instr_name, "type": instr_type, "sector_timing": sector_timing}
    return matrix

# ---------------------------------------------------------------------------
# Macro Layer
# ---------------------------------------------------------------------------
def get_macro_context():
    return {
        "fed_rate": round(random.uniform(4.25, 5.5), 2),
        "us10y": round(random.uniform(3.8, 4.8), 2),
        "dxy": round(random.uniform(100, 108), 2),
        "india_vix": round(random.uniform(10, 30), 2),
        "usd_inr": round(random.uniform(82.5, 84.5), 2),
        "rbi_repo": round(random.uniform(6.0, 7.0), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/instruments")
def api_instruments():
    data = []
    for sym, name, typ in GLOBAL_INSTRUMENTS:
        p = _instrument_prices.get(sym, {})
        data.append({"symbol": sym, "name": name, "type": typ,
                     "price": p.get("price"), "change_pct": p.get("change_pct"),
                     "high": p.get("high"), "low": p.get("low")})
    return jsonify(data)

@app.route("/api/companies")
def api_companies():
    sector_filter = request.args.get("sector")
    companies = []
    for sym, name, sector in NIFTY_50_COMPANIES:
        if sector_filter and sector != sector_filter:
            continue
        profile = COMPANY_PROFILES.get(sym, {})
        companies.append({"symbol": sym, "name": name, "sector": sector,
            "currency_sensitivity": profile.get("currency_sensitivity"),
            "interest_rate_sensitivity": profile.get("interest_rate_sensitivity"),
            "volatility_character": profile.get("volatility_character"),
            "lead_lag": profile.get("lead_lag"),
            "supply_chain_dependency": profile.get("supply_chain_dependency"),
            "regulatory_exposure": profile.get("regulatory_exposure")})
    return jsonify(companies)

@app.route("/api/company/<symbol>")
def api_company_detail(symbol):
    for sym, name, sector in NIFTY_50_COMPANIES:
        if sym == symbol:
            profile = COMPANY_PROFILES.get(sym, {})
            base_price = random.uniform(500, 5000)
            price_data = []
            for i in range(30):
                d = (datetime.now(timezone.utc) - timedelta(days=29-i)).isoformat()
                change = random.gauss(0, 0.015)
                base_price *= (1 + change)
                price_data.append({"date": d, "close": round(base_price, 2), "volume": round(random.uniform(1e6,5e6),0)})
            return jsonify({"symbol": sym, "name": name, "sector": sector,
                "profile": {"currency_sensitivity": profile.get("currency_sensitivity"),
                    "interest_rate_sensitivity": profile.get("interest_rate_sensitivity"),
                    "volatility_character": profile.get("volatility_character"),
                    "lead_lag": profile.get("lead_lag"),
                    "supply_chain_dependency": profile.get("supply_chain_dependency"),
                    "regulatory_exposure": profile.get("regulatory_exposure"),
                    "commodity_exposure": profile.get("commodity_exposure", {})},
                "price_data": price_data})
    return jsonify({"error": "Company not found"}), 404

@app.route("/api/sectors")
def api_sectors():
    counts = defaultdict(int)
    for _, _, s in NIFTY_50_COMPANIES:
        counts[s] += 1
    return jsonify([{"sector": k, "count": v} for k, v in sorted(counts.items())])

@app.route("/api/signals")
def api_signals():
    limit = request.args.get("limit", 20, type=int)
    if random.random() < 0.4:
        evidence_engine.generate_signals()
    return jsonify(evidence_engine.get_active_signals(limit))

@app.route("/api/signals/generate", methods=["POST"])
def api_generate_signals():
    signals = evidence_engine.generate_signals()
    return jsonify({"generated": len(signals), "signals": signals})

@app.route("/api/forecasts")
def api_forecasts():
    return jsonify(generate_forecasts())

@app.route("/api/leadlag")
def api_leadlag():
    return jsonify(get_lead_lag_matrix())

@app.route("/api/macro")
def api_macro():
    return jsonify(get_macro_context())

@app.route("/api/summary")
def api_summary():
    sectors_data = defaultdict(lambda: {"count": 0, "positive": 0, "negative": 0})
    for sym, name, sector in NIFTY_50_COMPANIES:
        sectors_data[sector]["count"] += 1
        r = random.random()
        if r < 0.45:
            sectors_data[sector]["positive"] += 1
        elif r < 0.9:
            sectors_data[sector]["negative"] += 1
    instr_data = []
    for sym, name, typ in GLOBAL_INSTRUMENTS:
        p = _instrument_prices.get(sym, {})
        instr_data.append({"symbol": sym, "name": name,
            "price": p.get("price"), "change_pct": p.get("change_pct"),
            "direction": "up" if (p.get("change_pct") or 0) > 0 else "down"})
    active_signals = evidence_engine.get_active_signals(5)
    macro = get_macro_context()
    return jsonify({
        "instruments": instr_data, "sectors": dict(sectors_data),
        "active_signals_count": len(active_signals),
        "high_confidence_signals": sum(1 for s in active_signals if s.get("confidence", 0) > 0.7),
        "macro": {"india_vix": macro["india_vix"], "usd_inr": macro["usd_inr"], "dxy": macro["dxy"]},
        "total_companies": len(NIFTY_50_COMPANIES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

if __name__ == "__main__":
    print("=" * 60)
    print(" NIFTY 50 Market Risk Engine - Dashboard Server")
    print("=" * 60)
    print(f" Companies loaded: {len(NIFTY_50_COMPANIES)}")
    print(f" Instruments: {len(GLOBAL_INSTRUMENTS)}")
    print(f" Sectors: {len(SECTORS)}")
    print("=" * 60)
    print(" Starting on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
