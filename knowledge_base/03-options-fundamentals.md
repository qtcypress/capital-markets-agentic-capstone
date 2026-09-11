---
doc_id: KB-03
title: Options Fundamentals
category: options
last_reviewed: 2026-08-15
authority: educational
---

# Options Fundamentals

## Calls, Puts and the Right Without Obligation

An option is a contract that gives its buyer a right, exercisable on defined terms, while imposing a corresponding obligation on its seller. A call option gives the buyer the right to buy the underlying at the strike price; a put option gives the buyer the right to sell the underlying at the strike price. The buyer pays a premium for that right, and once paid the premium is sunk — it is the buyer's entire maximum loss.

The seller, called the writer, receives the premium and accepts the mirror obligation. A call writer must deliver the underlying (or settle in cash) if the call is exercised; a put writer must take the underlying (or settle in cash) if the put is exercised. Because the obligation is open-ended in one direction, the writer's potential loss is far larger than the premium received, and writers therefore post margin with the clearing corporation.

In the Indian market, exchange-traded index and stock options are European-style, meaning exercise is possible only at expiry rather than at any time before it. In practice, positions are almost always closed by trading the option back in the market rather than by holding to exercise, and only positions still open at expiry go through the exchange's automatic exercise of in-the-money contracts.

Index options are cash-settled; single-stock options are physically settled at expiry, so an in-the-money single-stock option carried through expiry becomes a share delivery obligation. That asymmetry between index and stock settlement is one of the most operationally significant facts in Indian options.

## Strike Price, Spot Price and Moneyness

Moneyness describes the relationship between an option's strike price and the current price of the underlying, and it is the primary organising concept for reading an option chain. A call is in-the-money when spot exceeds strike, at-the-money when spot approximately equals strike, and out-of-the-money when spot is below strike. A put is in-the-money when spot is below strike, at-the-money when spot approximately equals strike, and out-of-the-money when spot exceeds strike.

Concretely, with NIFTY spot at 24,000, the 23,800 call is in-the-money by 200 points, the 24,000 call is at-the-money and the 24,200 call is out-of-the-money. The same three strikes for puts invert: the 24,200 put is in-the-money, the 24,000 put is at-the-money and the 23,800 put is out-of-the-money.

Strikes are listed at intervals set by the exchange — an illustrative 50-point interval for NIFTY, 100 points for BANKNIFTY, with wider intervals further from spot — and the exchange introduces additional strikes as spot moves. Strike intervals and the number of strikes listed are exchange parameters revised periodically; verify against the current exchange/SEBI circular before relying on this.

Moneyness matters because it determines the composition of premium between intrinsic and time value, the option's sensitivity profile, and its liquidity. Deep out-of-the-money strikes trade thinly with wide spreads; strikes near spot carry the bulk of volume and open interest.

## Intrinsic Value and Time Value

Every option premium decomposes into intrinsic value and time value, and separating the two is the first analytical step in reading any option price. Intrinsic value is the amount by which the option is in-the-money right now, floored at zero: for a call it is max(S − K, 0), and for a put it is max(K − S, 0). Intrinsic value can never be negative because the buyer would simply not exercise.

Time value, sometimes called extrinsic value, is whatever remains of the premium after intrinsic value is subtracted. It compensates the writer for the possibility that the underlying moves further in the buyer's favour before expiry. Time value depends on time remaining, on the volatility expected over that time, on interest rates and, for stocks, on expected dividends.

An illustration: NIFTY spot is 24,000 and the 23,800 call trades at 280. Intrinsic value is 24,000 − 23,800 = 200, so time value is 80. The 24,200 call, out-of-the-money, has intrinsic value zero, so its entire premium — say 95 — is time value. Comparing the two shows that at-the-money and near-the-money options carry the largest absolute time value, while deep in-the-money options are dominated by intrinsic value.

Time value decays toward zero as expiry approaches and reaches exactly zero at expiry, when premium equals intrinsic value. That terminal condition is what makes expiry-day option behaviour so different from behaviour weeks earlier, and it is the economic content of the Greek called theta.

## Option Payoffs at Expiry

Option payoffs at expiry are piecewise-linear functions of the settlement price, and writing them out precisely removes most of the confusion that surrounds options. For a long call struck at K bought for premium c, the payoff per unit at settlement price ST is max(ST − K, 0) − c. For a long put struck at K bought for premium p, it is max(K − ST, 0) − p. For a short call it is c − max(ST − K, 0), and for a short put it is p − max(K − ST, 0). Each is multiplied by the lot size to convert to rupees.

A numerical illustration using NIFTY with lot size 75: a trader buys the 24,000 call for 150. If NIFTY settles at 24,400, the payoff per unit is 400 − 150 = 250, so the lot gains 18,750 rupees. If NIFTY settles at 24,000 or anywhere below, the call expires worthless and the loss is the full premium, 150 × 75 = 11,250 rupees. Breakeven is 24,150.

The shape matters more than any single number. Long option payoffs are convex — bounded loss, unbounded or large gain — while short option payoffs are concave, with bounded gain and large or unbounded loss. Because the writer's gain is capped at the premium while the loss is not, writing naked options is a fundamentally different risk undertaking from buying them, regardless of how probable each outcome appears. This document describes payoff mechanics only and makes no recommendation about either side.

## Put-Call Parity

Put-call parity is the no-arbitrage relationship that links the prices of a European call and a European put with the same underlying, the same strike and the same expiry. In its standard form for a non-dividend-paying underlying it states:

C - P = S - K*e^(-rT)

Here C is the call premium, P is the put premium, S is the current spot price, K is the strike, r is the continuously compounded risk-free rate and T is the time to expiry in years. This project's models use a risk-free rate of 6.5 percent; verify against the current exchange/SEBI circular and prevailing market rates before relying on this.

The relationship follows from constructing two portfolios with identical terminal values. Holding a call and shorting a put replicates a forward commitment to buy at K; holding the underlying and borrowing the present value of K replicates the same thing. Since both portfolios pay ST − K at expiry regardless of outcome, they must cost the same today, or a riskless profit exists.

A worked illustration: NIFTY spot 24,000, strike 24,000, r 6.5 percent, T 30 days (0.0822 years). K*e^(-rT) = 24,000 × e^(-0.005343) ≈ 23,872. So C − P should be approximately 128. If the 24,000 call trades at 300, the put should trade near 172.

For a dividend-paying underlying, the spot term is reduced by the present value of dividends expected before expiry, giving C − P = S − PV(D) − K*e^(-rT). Deviations from parity in practice are bounded by transaction costs, borrowing constraints and, in India, the difficulty of shorting the cash underlying.

## Synthetic Positions Built from Parity

Synthetic positions are combinations of options, futures and the underlying that replicate the payoff of a different instrument, and put-call parity is the algebra that generates them. Rearranging C − P = S − K*e^(-rT) gives every synthetic identity a practitioner needs.

A synthetic long underlying is a long call plus a short put at the same strike and expiry: its payoff mimics owning the underlying, financed. A synthetic short underlying is a short call plus a long put. A synthetic long call is a long underlying (or long future) plus a long put — the classic protective put, whose payoff shape is identical to a call. A synthetic long put is a short underlying plus a long call. A synthetic short call is a short underlying plus a short put, and a synthetic short put is a long underlying plus a short call, which is the covered call.

These identities matter for three practical reasons. First, they let a trader construct an exposure through whichever legs are most liquid or most margin-efficient. Second, they mean apparent price discrepancies between a synthetic and its direct equivalent are arbitrage signals — a "conversion" buys the cheaper form and sells the dearer. Third, they clarify risk: recognising that a covered call is a synthetic short put makes obvious that its downside is the same as a short put's, which is not always intuitive to holders who think of it as a conservative income strategy.

In the Indian market, synthetic construction is constrained by the difficulty of shorting cash equity, so futures are usually substituted for the short-underlying leg.

## Implied Volatility and the Volatility Surface

Implied volatility is the volatility number that, when substituted into an option pricing model, reproduces the option's observed market price. It is not a forecast published by anyone; it is an inversion of the pricing formula, and it is the market's collective quotation of expected future variability expressed in annualised percentage terms. Because premium rises monotonically with volatility in standard models, there is exactly one implied volatility consistent with any given premium.

Implied volatility differs from historical or realised volatility, which is computed from past price movements. The two need not agree, and the gap between them is itself a widely studied quantity. India's volatility index, India VIX, is constructed from NIFTY option prices and is commonly used as a summary measure of near-term expected NIFTY volatility.

Implied volatility is not a single number across a contract chain. Plotted against strike for a fixed expiry it typically forms a skew or smile: out-of-the-money puts frequently carry higher implied volatility than equidistant out-of-the-money calls in equity markets, reflecting demand for downside protection and the empirical tendency of equity returns to have fat left tails. Plotted against expiry for a fixed strike it forms a term structure, which can slope up or down. The two dimensions together form the volatility surface.

For a trader, the surface has practical consequences: two options on the same underlying can be priced with very different volatilities, so a strategy that is long one strike and short another is implicitly a trade on the relative shape of the surface, not merely on direction.

## Black-Scholes and Its Assumptions

The Black-Scholes-Merton model is the standard reference framework for European option pricing and the model most commonly used to compute implied volatility and Greeks for Indian index and stock options. Its call formula is C = S × N(d1) − K × e^(−rT) × N(d2), with d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T) and d2 = d1 − σ√T, where N is the cumulative standard normal distribution and σ is volatility. The put price follows from put-call parity.

The model rests on assumptions that are known to be imperfect. It assumes the underlying follows a geometric Brownian motion with constant volatility, that trading is continuous and frictionless, that the risk-free rate is constant and known, that there are no transaction costs or taxes, that short selling is unrestricted, and that no dividends are paid over the option's life unless a dividend adjustment is added. It also assumes European exercise, which happens to fit Indian exchange-traded options well.

Real markets violate several of these. Volatility is not constant — the existence of the volatility smile is direct evidence of that. Prices jump on news rather than moving continuously. Short selling in Indian cash equity is constrained. Transaction costs and taxes are material. Practitioners therefore treat Black-Scholes not as a truth but as a common language: a standardised transformation between price and implied volatility, and a source of internally consistent Greeks. This project's models use a risk-free rate of 6.5 percent as the r input; verify against the current exchange/SEBI circular and prevailing market rates before relying on this.

## Reading an Option Chain

An option chain is the tabular display of all listed strikes for one underlying and one expiry, with calls conventionally on the left, strikes down the centre and puts on the right. Each side shows, at minimum, the last traded price, bid and ask, bid and ask quantities, traded volume, open interest, change in open interest and implied volatility. Reading it fluently is a basic operational skill.

Several patterns recur. Liquidity is highest at and near the at-the-money strike and decays as strikes move away, so bid-ask spreads widen with distance from spot. Open interest often clusters at round-number strikes, which market commentary interprets as support or resistance, though such interpretation is inference rather than mechanism. Implied volatility read across strikes reveals the skew described earlier.

Two cautions apply to chain data. First, last traded price can be stale for illiquid strikes, sometimes hours old, which makes it a poor basis for valuation; the mid of a live bid-ask is more informative, and a strike with no bid or no ask is effectively untradeable in that direction. Second, open interest is published with a lag in some feeds and is a stock rather than a flow, so change in open interest is the more informative field for activity.

For an automated system, the chain should be consumed with explicit staleness checks, explicit handling of missing quotes, and lot size read from the exchange contract specification master rather than assumed. Strike ranges and the number of strikes available are exchange parameters revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Weekly and Monthly Expiries in Indian Options

Indian index options are listed with both weekly and monthly expiries, and the distinction drives most of the market's activity pattern. Weekly expiry days used by this project are NIFTY on Thursday, BANKNIFTY on Wednesday, FINNIFTY on Tuesday and MIDCPNIFTY on Monday. Monthly expiry is the last Thursday of the month, and where an expiry day falls on a trading holiday, expiry shifts to the preceding business day. The set of indices carrying weekly options and the specific weekday assigned to each has been changed by the exchanges more than once; verify against the current exchange/SEBI circular before relying on this.

Single-stock options in India are listed on monthly expiries only, and they are physically settled. Index options are cash-settled against the index's final settlement value, computed from an averaged closing window rather than a single print.

The economic consequence of short-dated expiries is concentrated theta and gamma. An option with one day to expiry has almost no time value but extremely high sensitivity of delta to price, so small index moves produce large percentage changes in premium. Volume in weekly options concentrates overwhelmingly in the final one or two sessions before their expiry.

Because four indices expire on four different weekdays in this project's convention, an options book spanning them has an expiry event nearly every trading day of the week. Position and risk systems must therefore track expiry by contract rather than by a single weekly calendar assumption.

## Exercise, Assignment and Automatic Exercise

Exercise and assignment are the terminal events of an option's life, and Indian conventions make them largely automatic. Exchange-traded index and stock options in India are European-style, so no exercise is possible before expiry. At expiry, the clearing corporation applies automatic exercise to all in-the-money options: the holder need take no action, and the option is exercised on their behalf against the final settlement value. Out-of-the-money options simply lapse worthless.

Assignment is the corresponding event for the writer. Short positions in in-the-money options are assigned, and the assignment is allocated across short holders by the clearing corporation's process. For index options, assignment produces a cash debit equal to the option's intrinsic value at settlement multiplied by the lot size. For single-stock options, assignment produces a physical delivery obligation: an assigned short call must deliver shares, an assigned short put must take delivery and pay.

The most dangerous case is a single-stock option that finishes marginally in-the-money and is assigned into physical settlement against a holder who expected it to lapse. One lot of an assigned SBIN option at lot size 750, or ITC at lot size 1600, creates a delivery obligation many times the premium involved.

Options very close to the money at expiry are especially uncertain, because the settlement value derives from an averaged closing window that is not known until the session ends. Traders managing single-stock option positions therefore typically close them rather than allow settlement to decide. Nothing in this document constitutes investment advice; it describes contract mechanics only.
