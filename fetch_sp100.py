"""
Build the real-asset model: the 100 largest S&P 500 companies.

Run once, with network. Writes data/sp100_model.npz and data/sp100_model.json
containing only DERIVED quantities -- tickers, weights, mean vector,
covariance matrix, fitted Student-t degrees of freedom. Raw prices are kept
in data/raw/ locally and are not meant for publication (Yahoo terms).
After this, every benchmark runs offline again.

Selection
---------
- Constituents and weights: SPDR S&P 500 ETF (SPY) daily holdings file,
  ranked by fund weight (= float-adjusted market cap).
- One line per company: share classes (GOOGL/GOOG) would give two almost
  perfectly correlated columns and a near-singular covariance. The larger
  line is kept.
- Full price history over the window is required. Companies listed or spun
  off inside the window are skipped and the next-largest one moves up; the
  skipped names are recorded in the JSON.
- Weights: SPY weights of the selected 100, renormalised to sum to 1.

Known bias, stated in the article: today's 100 largest, looked at over the
past five years, is a survivorship-biased universe. For a benchmark of
compute time and estimator error that is harmless; for a performance study
it would not be.

Estimation
----------
Daily log returns. Mean vector and sample covariance over the full window.
Student-t: nu fitted by maximum likelihood to the historical daily returns of
the weighted portfolio (scipy.stats.t.fit). Under a multivariate t, the
portfolio return is univariate t with the same nu, so this is the one
parameter the risk measure actually sees.
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.request
from pathlib import Path

import numpy as np

SPY_URL = ("https://www.ssga.com/us/en/intermediary/library-content/products/"
           "fund-data/etfs/us/holdings-daily-us-en-spy.xlsx")
START, END = "2021-09-23", "2026-09-24"      # yfinance end is exclusive
N_ASSETS = 100
MIN_COVERAGE = 0.99                          # share of trading days required

DATA = Path(__file__).parent / "data"
RAW = DATA / "raw"


def fetch_holdings() -> tuple[list[dict], str]:
    """SPY daily holdings (xlsx). iShares' IVV CSV link returns an HTML page
    for European visitors, so the SPDR file is used; both track the same
    index with float-adjusted market-cap weights."""
    import pandas as pd
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "SPY_holdings.xlsx"
    if not path.exists():
        req = urllib.request.Request(SPY_URL, headers={"User-Agent": "Mozilla/5.0"})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    head = pd.read_excel(path, header=None, nrows=4)
    as_of = str(head.iloc[2, 1]).replace("As of", "").strip()
    df = pd.read_excel(path, header=4)
    df = df[pd.to_numeric(df["Weight"], errors="coerce").notna()]
    df = df[df["Ticker"].astype(str).str.fullmatch(r"[A-Z][A-Z.]*")]
    rows = [{"Ticker": t, "Name": n, "w": float(w)}
            for t, n, w in zip(df["Ticker"], df["Name"], df["Weight"])]
    rows.sort(key=lambda r: r["w"], reverse=True)
    return rows, as_of


def yahoo_symbol(t: str) -> str:
    return t.replace(".", "-").replace("/", "-")      # BRK.B -> BRK-B


def company_key(name: str) -> str:
    """Collapse share classes: 'ALPHABET INC CLASS A' -> 'ALPHABET INC'."""
    n = name.upper()
    for tag in (" CLASS A", " CLASS B", " CLASS C", " CL A", " CL B", " CL C"):
        n = n.replace(tag, "")
    return n.strip()


def main():
    import yfinance as yf
    from scipy import stats

    holdings, as_of = fetch_holdings()
    print(f"SPY holdings as of {as_of}: {len(holdings)} equity lines")

    # Candidates: one line per company, generous head so skips can be filled.
    seen, cands = set(), []
    for r in holdings:
        k = company_key(r["Name"])
        if k in seen:
            continue
        seen.add(k)
        cands.append(r)
        if len(cands) >= N_ASSETS + 40:
            break

    syms = [yahoo_symbol(r["Ticker"]) for r in cands]
    px = yf.download(syms, start=START, end=END, auto_adjust=True,
                     progress=False, threads=True)["Close"]
    px.to_csv(RAW / "prices_close.csv")
    days = len(px.index)

    chosen, skipped = [], []
    for r, s in zip(cands, syms):
        cov = px[s].notna().mean() if s in px else 0.0
        if cov >= MIN_COVERAGE and len(chosen) < N_ASSETS:
            chosen.append((r, s))
        elif len(chosen) < N_ASSETS:
            skipped.append({"ticker": r["Ticker"], "name": r["Name"],
                            "coverage": round(float(cov), 3)})
    assert len(chosen) == N_ASSETS, f"only {len(chosen)} usable assets"

    cols = [s for _, s in chosen]
    p = px[cols].ffill().dropna()
    rets = np.log(p).diff().dropna().to_numpy()          # (T, 100) daily
    mu = rets.mean(axis=0)
    cov = np.cov(rets, rowvar=False)
    w = np.array([r["w"] for r, _ in chosen])
    w /= w.sum()
    np.linalg.cholesky(cov)                               # must be PD

    port = rets @ w
    nu, loc, scale = stats.t.fit(port)

    DATA.mkdir(exist_ok=True)
    np.savez(DATA / "sp100_model.npz", mu=mu, cov=cov, w=w, nu=nu,
             tickers=np.array([r["Ticker"] for r, _ in chosen]))
    eig = np.linalg.eigvalsh(cov)[::-1]
    meta = {
        "source_holdings": "SPDR S&P 500 ETF (SPY) daily holdings, ssga.com",
        "holdings_as_of": as_of,
        "prices": "Yahoo Finance via yfinance, adjusted close",
        "window": [START, END], "trading_days": int(rets.shape[0]),
        "downloaded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "n_assets": N_ASSETS,
        "tickers": [r["Ticker"] for r, _ in chosen],
        "names": [r["Name"] for r, _ in chosen],
        "weights": w.round(6).tolist(),
        "skipped_incomplete_history": skipped,
        "portfolio_daily_vol": float(np.sqrt(w @ cov @ w)),
        "student_t_nu": float(nu),
        "variance_share_first_pc": float(eig[0] / eig.sum()),
        "variance_share_first_5_pc": float(eig[:5].sum() / eig.sum()),
    }
    (DATA / "sp100_model.json").write_text(json.dumps(meta, indent=2))
    print(f"{N_ASSETS} assets, {rets.shape[0]} days, skipped {len(skipped)}")
    print(f"portfolio daily vol {meta['portfolio_daily_vol']:.4%}, "
          f"t nu = {nu:.2f}, first PC {meta['variance_share_first_pc']:.1%}, "
          f"first 5 PCs {meta['variance_share_first_5_pc']:.1%}")


if __name__ == "__main__":
    main()
