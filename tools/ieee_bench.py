"""The benchmark Q&A set the RAGAS-style metrics are scored against.

Version-controlled on purpose: a RAGAS score is meaningless unless the question
set behind it is fixed. Change this file and every G02 threshold needs revisiting.
"""
RAGAS_BENCH = [
    dict(question="What is put-call parity?",
         truth="Put-call parity states that a call minus a put equals the spot price minus the "
               "present value of the strike, for European options on the same underlying, strike "
               "and expiry. An arbitrage exists when the relationship breaks.",
         entities=["call", "put", "strike", "expiry"]),
    dict(question="How does physical settlement work for stock F&O?",
         truth="Stock futures and options that remain open at expiry settle by physical delivery of "
               "the underlying shares, requiring the full contract value rather than margin, with "
               "delivery obligations netted across positions.",
         entities=["physical", "delivery", "expiry", "shares"]),
    dict(question="What is theta decay in options?",
         truth="Theta measures the loss of option value with the passage of time, accelerating as "
               "expiry approaches and affecting option buyers negatively and sellers positively.",
         entities=["theta", "time", "expiry", "premium"]),
    dict(question="What is SPAN margin?",
         truth="SPAN margin is the portfolio risk margin computed by the exchange from a scenario "
               "grid of price and volatility moves, to which an exposure margin is added.",
         entities=["span", "exposure", "margin", "portfolio"]),
]
