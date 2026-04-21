import yfinance as yf

tickers = {
    "코스닥":   "^KQ11",
    "비트코인": "BTC-USD",
    "금":       "GC=F",
    "유가":     "CL=F",
}

for name, ticker in tickers.items():
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if len(hist) > 0:
            print(f"{name}: OK - 최근가 {round(hist['Close'].iloc[-1], 2)}")
        else:
            print(f"{name}: 데이터 없음")
    except Exception as e:
        print(f"{name}: 오류 - {e}")