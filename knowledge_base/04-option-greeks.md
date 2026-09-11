---
doc_id: KB-04
title: Option Greeks
category: options
last_reviewed: 2026-08-15
authority: educational
---

# Option Greeks

## What the Greeks Measure

The Greeks are the partial derivatives of an option's theoretical value with respect to the variables that determine it, and they are the standard language for describing option risk. An option's price depends on the underlying price, the time remaining, the volatility assumed, the interest rate and, for stocks, expected dividends. Each Greek isolates the sensitivity to one of these while holding the others fixed.

The first-order Greeks are delta (sensitivity to underlying price), theta (sensitivity to the passage of time), vega (sensitivity to volatility) and rho (sensitivity to the interest rate). Gamma is second-order in the underlying price: it measures how delta itself changes. Higher-order and cross Greeks such as vanna, volga, charm and speed refine the picture further.

Two properties of the Greeks govern how they should be used. First, they are local: a delta of 0.55 describes behaviour for a small move, not for a ten percent gap, because the Greek itself changes as conditions change. Second, they are additive across positions on the same underlying, which is what makes portfolio-level risk aggregation possible — a book's net delta is the sum of the deltas of its legs, each scaled by lot size and position sign.

Greeks are model outputs, not observables. Values depend on the model and inputs used; this project computes them under Black-Scholes with a risk-free rate of 6.5 percent. Verify rate and other model conventions against current market data before relying on them.

## Delta

Delta measures the rate of change of an option's price with respect to a one-unit change in the underlying price, and it is the Greek that describes directional exposure. Call deltas range from 0 to +1 and put deltas from −1 to 0, under the convention that put deltas are expressed as negative numbers. A long futures position has a delta of +1 per unit of underlying; a short futures position, −1.

Delta varies with moneyness. A deep out-of-the-money call has a delta near zero — the underlying can move and the option barely responds. An at-the-money call has a delta near 0.5. A deep in-the-money call has a delta approaching 1 and behaves almost like the underlying itself. Puts mirror this: deep out-of-the-money near 0, at-the-money near −0.5, deep in-the-money near −1.

Delta serves three roles. As a sensitivity, it estimates rupee profit and loss: a NIFTY 24,000 call with delta 0.52, lot size 75, gains roughly 0.52 × 75 = 39 rupees per index point, so a 100-point rise adds about 3,900 rupees before other effects. As a hedge ratio, it says how much underlying or futures exposure offsets an option position — a short call with delta 0.52 on one NIFTY lot is hedged by holding 0.52 lots of futures, rounded to what is tradeable. As a rough proxy, absolute delta approximates the model's probability that the option finishes in-the-money, though this is an approximation rather than an identity.

Delta is not constant, and its instability is the subject of gamma.

## Gamma

Gamma measures the rate of change of delta with respect to the underlying price — the curvature of the option's value function — and it is what makes options fundamentally non-linear instruments. Gamma is positive for all long option positions, both calls and puts, and negative for all short option positions. Futures have zero gamma because their delta is constant.

Gamma is largest for at-the-money options and decays as the option moves deep in or deep out of the money. Crucially, gamma for at-the-money options increases sharply as expiry approaches. A NIFTY at-the-money option with three weeks to expiry has modest gamma; the same strike on expiry morning has extreme gamma, because its delta must transition from near 0.5 to either 0 or 1 within hours.

The practical meaning of positive gamma is that a long option position's delta moves in the holder's favour: as the underlying rises, a long call's delta increases, so the position gains at an accelerating rate; as it falls, delta shrinks, so losses decelerate. Negative gamma is the reverse and is why short option positions can deteriorate faster than a linear estimate suggests. A short straddle held into expiry day has large negative gamma, meaning a modest index move produces a loss much larger than the initial delta implied.

Gamma also governs hedging cost. A delta-hedged long option position must be rebalanced as the underlying moves, and positive gamma makes each rebalance profitable in isolation — buying low and selling high — which is the economic offset to paying theta. Short gamma inverts both signs.

## Theta

Theta measures the rate at which an option's value changes with the passage of time, holding all else constant, and it is conventionally quoted as the change in premium per calendar day. Long option positions have negative theta: they lose value each day because time value erodes. Short option positions have positive theta: they gain value as the same erosion works in the writer's favour.

Theta is not uniform across the option's life. Time value for an at-the-money option decays roughly in proportion to the square root of time remaining, which means decay accelerates as expiry approaches. An at-the-money NIFTY option with 30 days to run might lose a small fraction of its time value on a given day; the same option on the final morning loses essentially all remaining time value within hours. Illustratively, if a NIFTY at-the-money weekly option has 60 points of time value with two sessions left, a large share of that erodes over those two sessions if the index stays put.

Theta is largest in absolute terms for at-the-money options and smaller for deep in-the-money or deep out-of-the-money strikes, because those carry less time value to lose. It also scales with volatility: a higher implied volatility means more time value and therefore more to decay.

A crucial pairing: theta and gamma have opposite signs for any option position. Long options pay theta and receive gamma; short options receive theta and pay gamma. There is no position that collects both, and any strategy marketed as "earning time decay" is by construction accepting negative gamma. This is a mechanical identity, not a judgement about either approach.

## Vega

Vega measures the sensitivity of an option's price to a change in implied volatility, conventionally quoted as the rupee change in premium per one percentage point change in volatility. Vega is positive for all long option positions — both calls and puts gain value when expected variability rises — and negative for all short positions. Futures have zero vega.

Vega is largest for at-the-money options and for options with more time to expiry, because a longer horizon gives volatility more opportunity to matter. A NIFTY monthly at-the-money option has substantially higher vega than the same strike expiring in two days. As expiry approaches, vega collapses toward zero: on the final session, volatility assumptions barely affect an option that is about to settle at intrinsic value.

An illustration: a NIFTY at-the-money monthly call with a vega of 12 gains about 12 points of premium if implied volatility rises from 13 percent to 14 percent, which at lot size 75 is 900 rupees per lot. If volatility falls a point instead, the same magnitude is lost. A trader who is directionally correct can still lose money if implied volatility contracts enough to offset the delta gain — a common outcome after an anticipated event resolves.

Vega risk is a distinct exposure from directional risk, and strategies exist specifically to isolate it. Long straddles are long vega; short strangles are short vega. Calendar spreads are typically long vega in the far leg and short in the near, making them net long vega with a term-structure dependency. Because vega aggregates across strikes with different implied volatilities, portfolio vega understates risk when the volatility surface moves non-uniformly.

## Rho

Rho measures the sensitivity of an option's price to a change in the risk-free interest rate, conventionally quoted as the change in premium per one percentage point change in the rate. Rho is positive for calls and negative for puts. The intuition follows from put-call parity: the present value of the strike, K*e^(-rT), falls as r rises, which raises C − P, so calls gain and puts lose.

Rho is the least consequential Greek for most Indian equity derivatives activity, for two reasons. First, it scales with time to expiry, and Indian index option volume is dominated by weekly contracts with days rather than months to run, so the discounting effect is small. Second, policy rates move in modest steps at scheduled intervals, so the input rarely jumps.

Magnitudes make this concrete. For a NIFTY at-the-money option with 30 days to expiry, spot 24,000 and a risk-free rate of 6.5 percent, rho might be on the order of a point or two of premium per percentage point of rate change — negligible against typical daily premium movement driven by delta and vega. For a long-dated option with a year to expiry, rho becomes material, since the discount factor applied to the strike is doing real work.

Where rho does matter operationally in India is in the pricing of longer-dated single-stock options, in the fair-value calculation for futures via cost of carry, and in arbitrage strategies whose entire return is the carry differential. This project's models use a risk-free rate of 6.5 percent; verify against the current exchange/SEBI circular and prevailing market rates before relying on this.

## Second-Order Greeks

Second-order Greeks measure how the first-order Greeks themselves change, and they matter for books large enough that a first-order approximation breaks down between rebalances. Gamma, covered separately above, is the best known: it is the second derivative of value with respect to spot. The others complete the picture.

Vanna is the sensitivity of delta to a change in implied volatility, equivalently the sensitivity of vega to a change in spot. It explains why a delta hedge computed at one volatility level becomes wrong when volatility shifts, and it is central to managing risk-reversal and skew positions.

Volga, also called vomma, is the second derivative of value with respect to volatility — the sensitivity of vega to volatility itself. Positions long volga gain when volatility becomes more volatile, which is why they are held by traders expressing views on the convexity of the volatility surface rather than its level.

Charm, or delta bleed, is the sensitivity of delta to the passage of time. It matters acutely near expiry: an at-the-money option's delta drifts materially overnight even if spot is unchanged, so a hedge set at Wednesday's close can be stale by Thursday's open.

Speed is the third derivative with respect to spot — the rate of change of gamma — and colour is the rate of change of gamma with time. Both become significant only for large books or very short-dated positions.

The general lesson is that all Greeks are local approximations. For expiry-day index options, where gamma and charm are extreme, scenario analysis over a grid of spot and volatility outcomes is more reliable than any Taylor expansion.

## Aggregating Greeks Across a Portfolio

Greeks aggregate additively across positions on the same underlying, and this additivity is the foundation of portfolio-level options risk management. Net delta is the sum over all legs of position quantity multiplied by lot size multiplied by per-unit delta, with short positions carrying a negative sign. Net gamma, theta, vega and rho are computed the same way. A book that is long 10 lots of NIFTY 24,000 calls at delta 0.52 and short 10 lots of NIFTY 24,200 calls at delta 0.38 has net delta of (10 × 75 × 0.52) − (10 × 75 × 0.38) = 390 − 285 = 105 units of NIFTY exposure.

Aggregation across different underlyings requires care. Adding NIFTY delta to BANKNIFTY delta produces a number with no clean interpretation, because a point of NIFTY and a point of BANKNIFTY are not comparable. The standard fix is to convert each to rupee delta — exposure per one percent move in that underlying — which gives a common unit. Beta-weighting to a single reference index is another approach, but it inherits the instability of beta estimates.

Vega aggregation carries an additional caveat: summing vega across expiries assumes the whole term structure shifts by the same amount, which it frequently does not. Books with meaningful calendar structure should report vega bucketed by expiry.

Practical risk reporting therefore shows net delta in rupee terms, net gamma as the rupee change in delta per one percent move, theta as rupees per day, and vega bucketed by expiry — alongside scenario tables that do not rely on linearisation at all.

## Delta Hedging and Gamma Scalping

Delta hedging is the practice of offsetting a position's directional exposure by taking an opposing position in the underlying or its futures, so that small moves in the underlying produce approximately no profit or loss. An option writer short 10 lots of NIFTY calls with delta 0.52 carries net delta of −390 units, which is neutralised by buying futures equivalent to +390 units — roughly 5.2 NIFTY lots at lot size 75, rounded to five, leaving a small residual.

The hedge is not static. Because the option has gamma, delta changes as the underlying moves, so the futures position must be rebalanced. For a long option position with positive gamma, rebalancing systematically involves selling futures after the index rises and buying after it falls, each rebalance locking in a small gain. This activity is called gamma scalping, and its cumulative revenue is the economic offset against the theta the long option position pays.

For a short option position the signs invert: rebalancing requires buying after rises and selling after falls, locking in small losses, which is the cost of the theta being collected. This is why short-gamma books lose money in choppy markets even when direction ends flat.

The economics turn on realised versus implied volatility. If realised movement exceeds what the option's implied volatility priced, gamma scalping revenue exceeds theta paid, and the long position profits; if realised movement is lower, theta dominates. Rebalancing frequency is a trade-off, since each adjustment incurs brokerage, taxes, exchange charges and slippage. This section describes hedging mechanics only and does not recommend any position.

## Greeks Near Expiry and on Expiry Day

Option Greeks behave in extreme and often counterintuitive ways in the final sessions before expiry, and Indian weekly index options make this a routine rather than occasional condition. As time to expiry shrinks toward zero, the option's value function converges to its kinked payoff diagram, and the Greeks reflect that convergence.

Delta becomes a step function. An at-the-money option's delta on expiry morning can swing between near 0.2 and near 0.8 on a modest index move, because the market is resolving a binary question. Gamma spikes to its highest level of the contract's life, concentrated in the strikes nearest spot, and falls away sharply for strikes even a little distant. Theta reaches its maximum rate: the remaining time value must go to zero within hours. Vega collapses toward zero, so implied volatility changes stop mattering. Rho is effectively irrelevant.

The operational consequences are significant. A delta hedge computed at the open can be badly wrong by midday. A position that appears small by initial margin can generate outsized profit and loss. Bid-ask spreads on near-the-money expiry-day strikes can widen abruptly during fast moves, and deep out-of-the-money strikes can print at anomalous prices in thin books — the freak-trade phenomenon covered in the operational-controls document.

With NIFTY expiring Thursday, BANKNIFTY Wednesday, FINNIFTY Tuesday and MIDCPNIFTY Monday under this project's convention, a multi-index book faces this regime on most days of the week. Risk systems should therefore drive expiry-day monitoring from full scenario grids over spot and time rather than from Greek-based linear approximations. Nothing in this document constitutes investment advice; it describes model mechanics only.
