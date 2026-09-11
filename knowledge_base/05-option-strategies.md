---
doc_id: KB-05
title: Option Strategies
category: options
last_reviewed: 2026-08-15
authority: educational
---

# Option Strategies

## How to Read a Strategy Payoff

An option strategy is a combination of option and underlying positions whose aggregate payoff at expiry has a shape different from any single leg, and reading that shape correctly requires three numbers: maximum profit, maximum loss and breakeven. This document states all three explicitly for each strategy described, using the project's standard lot sizes and illustrative premiums so that the arithmetic can be checked.

Maximum profit is the best attainable outcome at expiry, net of premiums paid and received. Maximum loss is the worst attainable outcome on the same basis. Breakeven is the settlement price or prices at which the strategy returns exactly zero. Where a payoff is unbounded in one direction, the corresponding figure is stated as unlimited rather than as a large number, because no finite bound exists.

Three conventions apply throughout. All figures are per unit of the underlying unless a rupee amount is stated, in which case the lot size has been applied. All figures ignore brokerage, securities transaction tax, exchange transaction charges, stamp duty, GST and slippage, each of which reduces profit and increases loss in practice. And all figures assume the position is held to expiry; a position closed earlier realises a different result because time value remains.

Standard lot sizes used here are illustrative: NIFTY 75, BANKNIFTY 30, FINNIFTY 65, MIDCPNIFTY 120, RELIANCE 500, TCS 175, INFY 400, HDFCBANK 550, ICICIBANK 700, SBIN 750, ITC 1600, AXISBANK 625. Verify against the current exchange/SEBI circular before relying on this. Nothing here is a recommendation to adopt any strategy.

## Long Call

A long call is the purchase of a call option, paying premium for the right to buy the underlying at the strike, and it produces a payoff that is bounded below by the premium paid and unbounded above. It is the simplest convex option position: loss is capped, gain is not.

Illustration: buy one lot of the NIFTY 24,000 call for a premium of 150, with a lot size of 75. The premium outlay is 150 × 75 = 11,250 rupees, and that outlay is the entire capital at risk.

**Maximum profit:** Unlimited. Payoff per unit is (ST − 24,000) − 150 for settlement above the strike, which grows without bound as ST rises. At a settlement of 24,600 the per-unit profit is 450, or 33,750 rupees per lot.

**Maximum loss:** Limited to the premium paid, 150 per unit or 11,250 rupees per lot. This occurs at any settlement at or below the strike of 24,000, where the call expires worthless.

**Breakeven:** Strike plus premium, 24,000 + 150 = 24,150 at expiry.

The position carries positive delta, positive gamma, positive vega and negative theta. That combination means it loses value with each day that passes if the underlying does not move, and it loses value if implied volatility contracts even when the underlying rises. A long call bought before a scheduled event and held through the event can therefore lose money despite a favourable move, because the volatility premium deflates once uncertainty resolves. Long calls in single-stock options are physically settled at expiry, so an in-the-money position carried to expiry becomes a share purchase obligation.

## Long Put

A long put is the purchase of a put option, paying premium for the right to sell the underlying at the strike, and it produces a payoff bounded below by the premium paid and bounded above only by the strike itself, since the underlying cannot fall below zero. It is the mirror image of the long call in direction, though not perfectly symmetric in maximum profit.

Illustration: buy one lot of the NIFTY 24,000 put for a premium of 140, with a lot size of 75. The outlay is 140 × 75 = 10,500 rupees, which is the entire capital at risk.

**Maximum profit:** Limited by the strike falling to zero — strike minus premium, or 24,000 − 140 = 23,860 per unit, which is 17,89,500 rupees per lot. This bound is theoretical for an index; in practice the profit is large but finite and grows as the underlying falls. Many practitioners describe long put profit as "substantial but capped at strike minus premium" for precisely this reason.

**Maximum loss:** Limited to the premium paid, 140 per unit or 10,500 rupees per lot, realised at any settlement at or above the strike of 24,000.

**Breakeven:** Strike minus premium, 24,000 − 140 = 23,860 at expiry.

The position carries negative delta, positive gamma, positive vega and negative theta. Because equity index implied volatility typically rises as markets fall, a long put often benefits from both delta and vega simultaneously in a decline — a property that also means puts are usually priced at higher implied volatility than equidistant calls, the volatility skew. A long put used against an existing holding is a protective put, which is a synthetic long call by put-call parity.

## Covered Call

A covered call is the combination of a long position in the underlying (or its futures) with a short call written against it, and the resulting payoff caps upside at the strike in exchange for the premium received. It is often described as an income strategy, but its risk profile is identical to a short put, which is the more honest way to see it.

Illustration: hold 500 shares of RELIANCE (one lot equivalent) purchased at 2,900, and write one lot of the 3,000 call for a premium of 60. The premium received is 60 × 500 = 30,000 rupees.

**Maximum profit:** Limited to (strike − purchase price) + premium received, or (3,000 − 2,900) + 60 = 160 per unit, which is 80,000 rupees per lot. This is realised at any settlement at or above the strike of 3,000, where the call is assigned and the shares are delivered at 3,000.

**Maximum loss:** Limited by the underlying falling to zero — purchase price minus premium received, or 2,900 − 60 = 2,840 per unit, which is 14,20,000 rupees per lot. The premium cushions the decline but does not protect against it; a covered call holder retains essentially the full downside of the shares.

**Breakeven:** Purchase price minus premium received, 2,900 − 60 = 2,840 at expiry.

The position carries positive but reduced delta, negative gamma, negative vega and positive theta. Because RELIANCE options are physically settled, an in-the-money short call at expiry results in delivery of the held shares against payment at the strike, which is why the shares must genuinely be held or the position is not covered at all. Writing a call against shares one does not hold is a naked short call, discussed below.

## Long Straddle

A long straddle is the simultaneous purchase of a call and a put at the same strike and expiry, and it produces a V-shaped payoff that profits from a large move in either direction while losing if the underlying stays near the strike. It is a pure long-volatility position with no directional bias at inception.

Illustration: buy one lot each of the NIFTY 24,000 call at 150 and the NIFTY 24,000 put at 140, lot size 75. Total premium paid is 290 per unit, or 21,750 rupees per lot.

**Maximum profit:** Unlimited on the upside, since the call's payoff grows without bound; substantial but bounded on the downside at (strike − total premium), or 24,000 − 290 = 23,710 per unit if the index fell to zero. The practical description is unlimited upside, very large downside profit.

**Maximum loss:** Limited to the total premium paid, 290 per unit or 21,750 rupees per lot. This occurs at a settlement exactly at the strike of 24,000, where both legs expire worthless.

**Breakeven:** Two breakevens — upper at strike plus total premium, 24,000 + 290 = 24,290, and lower at strike minus total premium, 24,000 − 290 = 23,710.

The position carries near-zero initial delta, large positive gamma, large positive vega and large negative theta. It is the most theta-expensive common structure, because both legs bleed time value. A long straddle therefore requires realised movement greater than the implied movement priced in, and it can lose money on a move that is directionally large but slower than the premium assumed.

## Short Straddle

A short straddle is the simultaneous sale of a call and a put at the same strike and expiry, collecting both premiums, and it produces an inverted-V payoff that profits when the underlying settles near the strike and loses when it moves far in either direction. Its loss is UNLIMITED on the upside and very large on the downside, which makes it one of the highest-risk common structures in the market.

Illustration: sell one lot each of the NIFTY 24,000 call at 150 and the NIFTY 24,000 put at 140, lot size 75. Total premium received is 290 per unit, or 21,750 rupees per lot.

**Maximum profit:** Limited to the total premium received, 290 per unit or 21,750 rupees per lot, realised only if the index settles exactly at the strike of 24,000.

**Maximum loss:** UNLIMITED. On the upside the short call's loss grows without any bound as the index rises, so no finite maximum exists. On the downside the loss is bounded only by the index falling to zero, at (strike − premium) = 23,710 per unit, or 17,78,250 rupees per lot. A 3 percent adverse gap on NIFTY — about 720 points — produces a loss of roughly (720 − 290) × 75 = 32,250 rupees per lot, already exceeding the entire premium collected.

**Breakeven:** Two breakevens — upper at 24,000 + 290 = 24,290 and lower at 24,000 − 290 = 23,710.

The position carries near-zero initial delta, large negative gamma, large negative vega and large positive theta. Negative gamma means losses accelerate as the underlying moves, and the margin requirement expands as the position deteriorates, so a short straddle can trigger a margin call at the same moment it becomes most expensive to close.

## Long Strangle

A long strangle is the purchase of an out-of-the-money call and an out-of-the-money put with the same expiry but different strikes, and it produces a flat-bottomed payoff that costs less than a straddle but requires a larger move to profit. It is a long-volatility position with a wider zone of maximum loss.

Illustration: buy one lot of the NIFTY 24,200 call at 95 and one lot of the NIFTY 23,800 put at 85, lot size 75. Total premium paid is 180 per unit, or 13,500 rupees per lot.

**Maximum profit:** Unlimited on the upside as the call's payoff grows without bound; on the downside bounded at (lower strike − total premium) = 23,800 − 180 = 23,620 per unit if the index fell to zero. The practical description is unlimited upside, very large downside profit.

**Maximum loss:** Limited to the total premium paid, 180 per unit or 13,500 rupees per lot. Unlike a straddle, this maximum is realised across an entire range — any settlement between the two strikes, 23,800 to 24,200 inclusive, leaves both legs worthless.

**Breakeven:** Two breakevens — upper at call strike plus total premium, 24,200 + 180 = 24,380, and lower at put strike minus total premium, 23,800 − 180 = 23,620.

The position carries near-zero initial delta, positive gamma, positive vega and negative theta. Compared with a straddle, the strangle costs less premium and so has a smaller maximum loss in rupees, but its breakevens are further apart, so it needs a bigger move to become profitable. It also has lower gamma near the money, so it responds less to small moves than a straddle does.

## Short Strangle

A short strangle is the sale of an out-of-the-money call and an out-of-the-money put with the same expiry but different strikes, collecting both premiums, and it produces a flat-topped payoff with UNLIMITED loss on the upside and very large loss on the downside. It is widely used precisely because the profit zone is wide, and it is widely misunderstood because the tail loss is unbounded.

Illustration: sell one lot of the NIFTY 24,200 call at 95 and one lot of the NIFTY 23,800 put at 85, lot size 75. Total premium received is 180 per unit, or 13,500 rupees per lot.

**Maximum profit:** Limited to the total premium received, 180 per unit or 13,500 rupees per lot, realised for any settlement between 23,800 and 24,200 inclusive.

**Maximum loss:** UNLIMITED. Above the call strike the loss grows without bound as the index rises; there is no finite maximum. Below the put strike the loss is bounded only by the index reaching zero, at (23,800 − 180) = 23,620 per unit, or 17,71,500 rupees per lot. A move to 25,000 produces a loss of (25,000 − 24,200 − 180) × 75 = 46,500 rupees per lot, more than three times the premium collected.

**Breakeven:** Two breakevens — upper at 24,200 + 180 = 24,380 and lower at 23,800 − 180 = 23,620.

The position carries near-zero initial delta, negative gamma, negative vega and positive theta. Because a large fraction of individual outcomes are profitable while a small fraction are severely loss-making, the strategy's win rate conveys almost nothing about its risk. Margin requirements rise sharply when volatility rises, compounding the pressure exactly when the position is losing.

## Naked Short Call and Why Its Loss Is Unlimited

A naked short call is the sale of a call option without holding the underlying or any offsetting long option, and its loss is UNLIMITED — the single most important fact about it. Because the underlying's price has no upper bound, the writer's obligation to deliver at the strike has no upper bound on its cost, and no finite maximum loss can be stated.

Illustration: sell one lot of the NIFTY 24,200 call at 95, lot size 75, collecting 7,125 rupees. If the index settles at 24,500 the loss is (300 − 95) × 75 = 15,375 rupees. At 25,000 the loss is (800 − 95) × 75 = 52,875 rupees. At 26,000 it is (1,800 − 95) × 75 = 1,27,875 rupees. The sequence does not converge.

**Maximum profit:** Limited to the premium received, 95 per unit or 7,125 rupees per lot, at any settlement at or below the strike of 24,200.

**Maximum loss:** UNLIMITED, growing linearly with the settlement price above the strike.

**Breakeven:** Strike plus premium, 24,200 + 95 = 24,295.

Two mechanisms make this worse than the arithmetic suggests. Gamma is negative, so the position's delta grows more short as the index rises, meaning each additional point costs more than the last. And margin requirements expand as the position moves in-the-money and as volatility rises, so the writer may be forced to close at the worst price. For single-stock options, an assigned naked short call creates an obligation to deliver shares the writer does not hold, resolved through the exchange's auction or close-out mechanism at a potentially punitive price.

## Bull Call Spread

A bull call spread is the purchase of a lower-strike call combined with the sale of a higher-strike call in the same expiry, and it produces a payoff with both profit and loss strictly bounded. It is the standard example of a defined-risk directional structure.

Illustration: buy one lot of the NIFTY 24,000 call at 150 and sell one lot of the NIFTY 24,200 call at 95, lot size 75. Net premium paid is 150 − 95 = 55 per unit, or 4,125 rupees per lot.

**Maximum profit:** Limited to the strike difference minus net premium paid, (24,200 − 24,000) − 55 = 145 per unit, or 10,875 rupees per lot. This is realised at any settlement at or above the higher strike of 24,200.

**Maximum loss:** Limited to the net premium paid, 55 per unit or 4,125 rupees per lot, realised at any settlement at or below the lower strike of 24,000.

**Breakeven:** Lower strike plus net premium paid, 24,000 + 55 = 24,055 at expiry.

The position carries positive delta, and its gamma, vega and theta are all small in net terms because the two legs largely offset. This muted Greek profile is the structure's defining characteristic: it responds mostly to direction and relatively little to volatility or time compared with a naked long call. The maximum-profit-to-maximum-loss ratio here is 145 to 55, and margining treats the spread far more favourably than two outright legs because scenario loss is capped. For single-stock spreads, both legs settle physically, so an expiry where one leg is in-the-money and the other is not creates a delivery obligation.

## Bear Put Spread

A bear put spread is the purchase of a higher-strike put combined with the sale of a lower-strike put in the same expiry, and it produces the downside mirror of a bull call spread — bounded profit if the underlying falls, bounded loss if it does not.

Illustration: buy one lot of the NIFTY 24,000 put at 140 and sell one lot of the NIFTY 23,800 put at 85, lot size 75. Net premium paid is 140 − 85 = 55 per unit, or 4,125 rupees per lot.

**Maximum profit:** Limited to the strike difference minus net premium paid, (24,000 − 23,800) − 55 = 145 per unit, or 10,875 rupees per lot. This is realised at any settlement at or below the lower strike of 23,800.

**Maximum loss:** Limited to the net premium paid, 55 per unit or 4,125 rupees per lot, realised at any settlement at or above the higher strike of 24,000.

**Breakeven:** Higher strike minus net premium paid, 24,000 − 55 = 23,945 at expiry.

The position carries negative delta with small net gamma, vega and theta. One subtlety specific to equity markets is the volatility skew: the higher-strike put bought is typically priced at a lower implied volatility than the lower-strike put sold, which can make the debit for a bear put spread slightly more favourable than the symmetric arithmetic of a bull call spread suggests, or less favourable depending on the skew's shape at the time. Because both maximum profit and maximum loss are bounded, this structure cannot produce a loss beyond the initial debit regardless of how far the underlying moves, and no margin call can arise from the option legs alone once the debit is paid.

## Iron Condor

An iron condor is a four-legged structure combining a short strangle with a wider long strangle around it: sell an out-of-the-money call and put, and buy a further out-of-the-money call and put in the same expiry. The long wings convert the short strangle's unlimited loss into a strictly bounded one, which is the entire point of the structure.

Illustration on NIFTY with lot size 75: sell the 24,200 call at 95, buy the 24,400 call at 45, sell the 23,800 put at 85, buy the 23,600 put at 40. Net premium received is (95 + 85) − (45 + 40) = 95 per unit, or 7,125 rupees per lot. Each wing is 200 points wide.

**Maximum profit:** Limited to the net premium received, 95 per unit or 7,125 rupees per lot, realised for any settlement between the short strikes, 23,800 to 24,200 inclusive.

**Maximum loss:** Limited to wing width minus net premium received, 200 − 95 = 105 per unit, or 7,875 rupees per lot. This is realised at any settlement at or above 24,400 or at or below 23,600. Unlike a short strangle, the loss is bounded no matter how far the underlying moves.

**Breakeven:** Two breakevens — upper at short call strike plus net premium, 24,200 + 95 = 24,295, and lower at short put strike minus net premium, 23,800 − 95 = 23,705.

The position carries near-zero initial delta, negative gamma, negative vega and positive theta, all smaller in magnitude than the equivalent naked short strangle. Because loss is capped, margin is materially lower than for a short strangle. The trade-off is that maximum profit is reduced by the cost of the wings, and the risk-reward here is 7,125 potential gain against 7,875 potential loss.

## Practical Considerations Across All Strategies

Every option strategy described in this document is affected by frictions and mechanics that the payoff arithmetic omits, and ignoring them is a reliable way to turn a theoretically sound structure into a losing one. Transaction costs come in layers: brokerage per order, securities transaction tax, exchange transaction charges, SEBI turnover fees, stamp duty and GST on brokerage and charges. A four-legged iron condor incurs eight order-level cost events if opened and closed, which on a structure whose maximum profit is 7,125 rupees per lot is a material fraction. Rates and charges change; verify against the current exchange/SEBI circular before relying on this.

Execution risk matters for multi-leg structures. Legging in — trading each leg separately — exposes the trader to the underlying moving between fills. Exchange-supported multi-leg or spread order types reduce this but are not available for every combination and may fill less readily.

Margining is not proportional to leg count. Defined-risk structures such as spreads and iron condors receive substantial margin offsets because scenario loss is capped, while short straddles and strangles attract large margins that expand with volatility. A margin expansion can force closure of a position that would have been profitable at expiry.

Settlement type must be checked before expiry. Index legs are cash-settled; single-stock legs are physically settled, so a spread on a stock can leave an unwanted delivery obligation if one leg finishes in-the-money. Nothing in this document is investment advice; it describes payoff mechanics only, and no strategy here is presented as suitable for any person or as likely to be profitable.
