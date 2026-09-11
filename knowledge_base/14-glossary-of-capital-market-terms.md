---
doc_id: KB-14
title: Glossary of Capital Market Terms
category: reference
last_reviewed: 2026-08-15
authority: educational
---

# Glossary of Capital Market Terms

## How to Use This Glossary

This glossary defines terms used across the Indian capital markets with an emphasis on equity derivatives, and it is organised by theme so that related concepts sit together. Each definition is written to stand alone: a reader arriving at a single entry should be able to understand it without having read the entries around it.

Definitions here are educational summaries in the author's own words, not statutory or exchange definitions. Where a term has a precise regulatory meaning — speculative transaction, market-wide position limit, unpublished price-sensitive information — the entry describes the concept rather than reproducing the legal text, and the operative definition is the one in the relevant SEBI circulars on the F&O framework, exchange rulebooks or statute.

Quantitative examples appearing in entries use this knowledge base's standard illustrative values: lot sizes of NIFTY 75, BANKNIFTY 30, FINNIFTY 65, MIDCPNIFTY 120, RELIANCE 500, TCS 175, INFY 400, HDFCBANK 550, ICICIBANK 700, SBIN 750, ITC 1600 and AXISBANK 625, a risk-free rate of 6.5 percent, weekly expiries on NIFTY Thursday, BANKNIFTY Wednesday, FINNIFTY Tuesday and MIDCPNIFTY Monday, and monthly expiry on the last Thursday. All such values are illustrative; verify against the current exchange/SEBI circular before relying on this.

Nothing in this glossary is investment advice. Entries describe what terms mean, not what any reader should do. Terms appearing in more than one theme are defined once, in the theme where they are most central, and cross-referenced by name elsewhere.

## Instruments and Contract Types

**Derivative** — A contract whose value is determined by reference to an underlying asset, index or rate, conferring no ownership of the underlying itself.

**Futures contract** — A standardised exchange-traded agreement obliging both parties to transact a specified quantity of an underlying at a fixed price on a fixed future date.

**Forward contract** — A privately negotiated agreement to transact at a future date, not exchange-traded and not centrally cleared, and therefore carrying bilateral credit risk.

**Option** — A contract giving its buyer a right, without a corresponding obligation, to buy or sell an underlying at a stated strike price, in exchange for a premium paid to the seller.

**Call option** — An option giving the buyer the right to buy the underlying at the strike price, identified by the suffix CE in Indian contract symbols.

**Put option** — An option giving the buyer the right to sell the underlying at the strike price, identified by the suffix PE in Indian contract symbols.

**European option** — An option exercisable only at expiry, which is the style used for exchange-traded index and stock options in India.

**American option** — An option exercisable at any time up to expiry, a style not used for Indian exchange-traded equity options.

**Index derivative** — A futures or option contract written on an equity index such as NIFTY, BANKNIFTY, FINNIFTY or MIDCPNIFTY, cash-settled at expiry in the Indian market.

**Single-stock derivative** — A futures or option contract written on an individual listed share, physically settled at expiry in the Indian market.

**Underlying** — The asset, index or reference whose price determines a derivative's value.

## Contract Specification Terms

**Lot size** — The number of units of the underlying represented by one derivative contract, also called the market lot; illustratively 75 for NIFTY and 500 for RELIANCE, and revised by the exchange from time to time.

**Notional value** — The economic size of a derivative position, computed as price multiplied by lot size multiplied by number of lots, distinct from the margin required to hold it.

**Strike price** — The price at which an option holder may buy or sell the underlying if the option is exercised.

**Strike interval** — The spacing between consecutive listed strikes in an option chain, narrower near the money and wider further away.

**Tick size** — The minimum permissible price increment for a contract, conventionally five paise for Indian equity derivatives.

**Expiry date** — The date on which a contract terminates and is settled; monthly expiry in this project is the last Thursday of the month, shifting to the preceding business day on a holiday.

**Weekly expiry** — A short-dated index option series expiring weekly; this project uses NIFTY Thursday, BANKNIFTY Wednesday, FINNIFTY Tuesday and MIDCPNIFTY Monday.

**Contract master** — The exchange file listing every tradeable contract with its full parameter set, and the authoritative source for lot size, tick size, expiry and settlement type.

**Instrument token** — The numeric identifier assigned by the exchange to a contract, the reliable primary key for automated systems.

**Quantity freeze** — The maximum quantity permitted in a single order for a contract, above which the order is held for exchange confirmation rather than executed directly.

**Price operating range** — The dynamic band around a reference price within which orders in a derivative contract may be priced; orders outside it are rejected.

## Option Pricing and Moneyness

**Premium** — The price paid by an option buyer to the seller, quoted per unit of the underlying and multiplied by lot size to give the rupee cost of one contract.

**Intrinsic value** — The amount by which an option is currently in-the-money, computed as max(S − K, 0) for a call and max(K − S, 0) for a put, and never negative.

**Time value** — The portion of an option's premium in excess of intrinsic value, reflecting the possibility of further favourable movement before expiry; it falls to zero at expiry.

**In-the-money (ITM)** — An option with positive intrinsic value: a call whose strike is below spot, or a put whose strike is above spot.

**At-the-money (ATM)** — An option whose strike is at or nearest to the current spot price, carrying the largest absolute time value.

**Out-of-the-money (OTM)** — An option with no intrinsic value: a call whose strike is above spot, or a put whose strike is below spot.

**Moneyness** — The relationship between an option's strike and the current spot price, determining the split between intrinsic and time value.

**Implied volatility** — The volatility input that, substituted into a pricing model, reproduces an option's observed market price; it is an inversion of the model, not a forecast.

**Historical volatility** — Volatility computed from past price movements of the underlying, distinct from implied volatility.

**Volatility skew** — The pattern in which implied volatility differs across strikes for one expiry, with equity out-of-the-money puts typically priced at higher implied volatility than equidistant calls.

**Volatility surface** — The full set of implied volatilities across both strike and expiry for one underlying.

**India VIX** — An index constructed from NIFTY option prices, used as a summary measure of expected near-term NIFTY volatility.

**Put-call parity** — The no-arbitrage relationship C - P = S - K*e^(-rT) linking European call and put prices with the same strike and expiry.

## The Greeks

**Delta** — The sensitivity of an option's price to a one-unit change in the underlying price, ranging from 0 to +1 for calls and −1 to 0 for puts, and equal to approximately +1 per unit for a long futures position.

**Gamma** — The rate of change of delta with respect to the underlying price, positive for all long option positions and negative for all short ones, and largest for at-the-money options near expiry.

**Theta** — The rate at which an option loses value with the passage of time, negative for long option positions and positive for short ones, accelerating as expiry approaches.

**Vega** — The sensitivity of an option's price to a one percentage point change in implied volatility, positive for long options, largest for at-the-money options with more time remaining, and collapsing toward zero at expiry.

**Rho** — The sensitivity of an option's price to a one percentage point change in the risk-free rate, positive for calls and negative for puts, and generally small for short-dated Indian index options.

**Vanna** — The sensitivity of delta to a change in implied volatility, equivalently the sensitivity of vega to the underlying price.

**Volga** — The second derivative of an option's value with respect to volatility, also called vomma.

**Charm** — The sensitivity of delta to the passage of time, also called delta bleed, and significant near expiry.

**Delta hedging** — Offsetting a position's directional exposure by taking an opposing position in the underlying or its futures.

**Gamma scalping** — Rebalancing the futures hedge of a long-gamma option position as the underlying moves, systematically selling into rises and buying into falls, which offsets theta paid.

## Strategy Vocabulary

**Long position** — A position that gains when the referenced contract rises in value; in options, a contract that has been bought with premium paid.

**Short position** — A position that gains when the referenced contract falls; in options, a contract that has been sold with premium received, carrying an obligation.

**Writer** — The seller of an option, who receives the premium and accepts the obligation, and who posts margin because the loss is not bounded by the premium.

**Covered call** — A long position in the underlying combined with a short call written against it, capping upside at the strike; economically equivalent to a short put.

**Protective put** — A long position in the underlying combined with a long put, bounding downside; economically equivalent to a long call by put-call parity.

**Straddle** — A call and a put at the same strike and expiry; long straddle is a long-volatility position with unlimited upside profit and loss capped at premium, short straddle has UNLIMITED loss.

**Strangle** — A call and a put at different out-of-the-money strikes in the same expiry; the short version has UNLIMITED loss on the upside.

**Bull call spread** — A long lower-strike call with a short higher-strike call in the same expiry, with both maximum profit and maximum loss strictly bounded.

**Bear put spread** — A long higher-strike put with a short lower-strike put in the same expiry, with both maximum profit and maximum loss strictly bounded.

**Iron condor** — A short strangle with a wider long strangle around it, converting the short strangle's unlimited loss into a bounded one.

**Calendar spread** — Simultaneous positions in two different expiries of the same underlying, isolating the difference between their bases.

**Breakeven** — The settlement price at which a strategy returns exactly zero, ignoring transaction costs.

**Synthetic position** — A combination of instruments replicating the payoff of a different instrument, derived from put-call parity.

## Margin and Clearing

**Margin** — Collateral deposited with the clearing corporation against the potential loss on a derivative position, returned when the position closes.

**SPAN** — Standardised Portfolio Analysis of Risk, the scenario-based portfolio margining methodology used to compute initial margin on Indian derivatives, charging the worst outcome across a defined set of price and volatility scenarios.

**Initial margin** — The portfolio scenario-based margin component covering a plausible one-day adverse move.

**Exposure margin** — An additional flat-rate margin layer, also called extreme loss margin, charged on notional value to cover moves beyond the scenario range.

**Premium margin** — The amount blocked from an option buyer, equal to the premium payable; option buyers post no scenario-based margin.

**Mark-to-market (MTM)** — The daily revaluation of futures positions against the daily settlement price, converting unrealised profit and loss into actual cash movement.

**Daily settlement price** — The exchange-computed price used for daily mark-to-market, conventionally derived from a volume-weighted average of trades in the closing window.

**Final settlement price** — The value at which contracts are settled at expiry, derived for indices from an averaged closing window and for single stocks from the cash market closing price.

**Peak margin** — The highest margin requirement observed across intraday snapshots of a client's positions, against which collateral adequacy is judged.

**Margin shortfall** — The condition in which available collateral is less than the margin required, attracting escalating penalties.

**Haircut** — The percentage reduction applied to the market value of non-cash collateral to arrive at its collateral value.

**Margin pledge** — The mechanism by which securities remain in the client's demat account while a pledge is created in favour of the broker and clearing corporation.

**Novation** — The legal replacement of a bilateral trade with two contracts facing the clearing corporation, making it counterparty to both sides.

**Cross-margining** — Recognition of offsetting risk across market segments, so that margin is charged on the net rather than the gross exposure.

## Market Structure and Trading

**Order book** — The list of resting buy and sell orders in a contract, ranked by price and, within a price level, by time of entry.

**Price-time priority** — The matching rule under which the best price executes first and, among orders at the same price, the earliest entered executes first.

**Bid-ask spread** — The difference between the best offer and the best bid, and the first component of round-trip trading cost.

**Market order** — An order to execute immediately at the best available prices, guaranteeing execution but not price.

**Limit order** — An order specifying the worst acceptable price, guaranteeing price but not execution.

**Immediate-or-cancel (IOC)** — An order that executes whatever quantity is available at entry and cancels the remainder without resting in the book.

**Stop-loss order** — A conditional order released into the book only when the market reaches a specified trigger price, available in limit and market variants.

**Cover order** — A broker product combining an entry order with a compulsory attached stop-loss, typically intraday only.

**Bracket order** — A broker product combining an entry, a stop-loss and a target, with execution of one protective leg cancelling the other.

**Slippage** — The difference between the price a trader intended and the price actually achieved, arising from latency, spread and market impact.

**Market impact** — The adverse price movement caused by an order consuming available depth and signalling demand.

**Circuit breaker** — An automatic trading halt triggered by defined percentage moves in a benchmark index, suspending trading across segments including derivatives.

**Freak trade** — An execution at a price far from prevailing levels, typically caused by a market order meeting a near-empty order book.

## Settlement and Expiry

**Cash settlement** — Termination of a contract by exchange of the money difference between contract terms and the final settlement value, used for all Indian index derivatives.

**Physical settlement** — Termination of a contract by actual delivery of shares against full payment, used for all Indian single-stock futures and options at expiry.

**Automatic exercise** — The clearing corporation's exercise of all in-the-money options at expiry without instruction from the holder.

**Assignment** — The allocation of an exercised option's obligation to a short position holder, producing a cash debit for index options and a delivery obligation for single-stock options.

**Do-not-exercise** — A facility, where available, allowing holders of specified close-to-the-money physically settled options to instruct that the option not be exercised.

**Rollover** — Closing an expiring position and simultaneously opening the equivalent position in the next expiry.

**Open interest** — The number of contracts outstanding at end of session, increasing only when a new long and new short are created together.

**Basis** — The difference between the futures price and the spot price of the same underlying, converging to zero at expiry.

**Contango** — The condition in which futures trade above spot, the normal state for equity futures when interest rates exceed dividend yield.

**Backwardation** — The condition in which futures trade below spot.

**Cost of carry** — The relationship F = S × e^((r − q) × T) anchoring the fair value of a futures contract to spot, interest rate and dividend yield.

**Auction** — The exchange mechanism for sourcing shares that a party has failed to deliver, with the cost charged to the defaulter.

**Close-out** — Cash settlement of a delivery failure at a reference price set by the shortage rules, deliberately unfavourable to the defaulter.

## Regulation, Risk and Taxation

**SEBI** — The Securities and Exchange Board of India, the statutory regulator of the Indian securities market, whose mandate combines investor protection, market development and regulation.

**Clearing corporation** — The institution that novates trades, computes and collects margin, runs settlement and maintains a settlement guarantee fund.

**Market-wide position limit (MWPL)** — The cap on aggregate open interest across all participants in a single stock's derivatives, computed from free float.

**F&O ban period** — The state in which aggregate open interest in a stock exceeds a defined threshold of its MWPL, during which only position-reducing orders are permitted.

**Client-level position limit** — The cap on derivative exposure a single client may hold in one underlying.

**Order-to-trade ratio** — The ratio of orders entered to trades executed, subject to limits and penalties to discourage excessive messaging.

**Kill switch** — A control allowing immediate disabling of an algorithm and cancellation of its open orders, required for approved algorithmic trading.

**Securities transaction tax (STT)** — A transaction-level levy on specified securities transactions, charged on the sell side for futures and option premium and on the buy side on settlement value for exercised options.

**Business income** — The head under which exchange-traded equity derivatives income in India is generally assessed, taxed at applicable slab or corporate rates with expenses deductible.

**Speculative transaction** — A transaction settled otherwise than by delivery; exchange-traded derivatives on a recognised exchange are generally excepted and treated as non-speculative.

**Derivatives turnover** — For tax purposes, computed as the absolute sum of favourable and unfavourable differences on settled transactions, not as notional value.

**Tax audit** — Examination and certification of accounts by a chartered accountant, required above prescribed turnover thresholds or in specified presumptive-taxation situations.

**Advance tax** — Income tax payable in instalments during the year in which income is earned, with interest charged on shortfall.

All definitions in this glossary are educational summaries, not statutory, regulatory or tax definitions, and nothing here is investment advice. Illustrative values change; verify against the current exchange/SEBI circular before relying on this.
