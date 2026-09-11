---
doc_id: KB-02
title: Futures Contracts and Pricing
category: derivatives
last_reviewed: 2026-08-15
authority: educational
---

# Futures Contracts and Pricing

## Definition and Standard Terms of a Futures Contract

A futures contract in the Indian equity derivatives market is a standardised, exchange-traded agreement to buy or sell a specified quantity of an underlying equity or index at a price fixed today, for settlement on a specified future date. Both parties are obliged; no premium is exchanged at inception. What each side deposits instead is margin with the clearing corporation, which is the counterparty to both after novation.

The standard terms are set by the exchange and published in the contract specification master. They comprise the underlying, the lot size (market lot), the expiry date, the tick size (the minimum price increment, typically five paise for equity derivatives), the price bands or operating ranges, the quantity freeze limit, the settlement type and the daily settlement price methodology. Traders negotiate only price and number of lots.

Indian equity futures are listed for three serial monthly expiries — near, next and far — with new far-month contracts introduced as the near month expires. Index futures may also be available in longer-dated or weekly forms depending on the exchange's product decisions at the time. Monthly expiry for this project is the last Thursday of the month; if that Thursday is a trading holiday, expiry moves to the preceding business day.

Index futures are cash-settled. Single-stock futures are physically settled at expiry, meaning an open position carried into expiry results in delivery or receipt of shares. Contract terms, tick sizes and freeze quantities are revised periodically; verify against the current exchange/SEBI circular before relying on this.

## The Futures Payoff and Its Linearity

The payoff of a futures contract is linear and symmetric, which is the property that makes futures the simplest derivative to reason about. For a long futures position entered at price F0, the profit at settlement price ST is (ST − F0) multiplied by the lot size and the number of lots. For a short position, the profit is (F0 − ST) times the same multiplier. Neither expression contains a maximum or a floor: the long's loss grows without limit as the price falls toward zero, and the short's loss grows without limit as the price rises.

A worked illustration makes the arithmetic concrete. A trader is long one lot of NIFTY futures at 24,000 with a lot size of 75. If the index settles at 24,300, the gain is 300 × 75 = 22,500 rupees. If it settles at 23,700, the loss is 300 × 75 = 22,500 rupees. The magnitudes are identical because the payoff is symmetric. For a single stock, one lot of RELIANCE futures at 2,900 with lot size 500 gains 50,000 rupees on a 100-rupee rise and loses the same on a 100-rupee fall.

Linearity means the position's sensitivity to the underlying is constant: a futures contract has a delta of approximately one per unit of underlying, and that delta does not change as the price moves. This constancy is why futures are the natural instrument for delta hedging an options book.

## Cost of Carry and the Fair Value of Futures

The fair value of an equity futures contract is anchored by the cost-of-carry relationship, which expresses the idea that buying the future should cost the same as borrowing money, buying the underlying today, and holding it to expiry. In continuous-compounding form, the theoretical futures price is F = S × e^((r − q) × T), where S is the spot price, r is the risk-free rate, q is the continuous dividend yield of the underlying and T is the time to expiry in years. This project's models use a risk-free rate of 6.5 percent; verify against the current exchange/SEBI circular and prevailing market rates before relying on this.

An illustration: with NIFTY spot at 24,000, r at 6.5 percent, negligible dividend yield over the horizon and T equal to 30 days (0.0822 years), the theoretical future is 24,000 × e^(0.065 × 0.0822) ≈ 24,000 × 1.00536 ≈ 24,128. The 128-point excess of futures over spot is the carry.

For single stocks with a meaningful dividend before expiry, the expected dividend reduces the futures price, because the futures holder does not receive it. If RELIANCE spot is 2,900, carry over the period is 20 rupees and an expected dividend of 10 rupees falls within the contract's life, fair value is approximately 2,910 rather than 2,920. The relationship is an equilibrium enforced by arbitrage, not an accounting identity, so observed prices deviate within transaction-cost bounds.

## Basis, Contango and Backwardation

Basis in the Indian equity derivatives market is conventionally the difference between the futures price and the spot price of the same underlying, and it is the single most watched diagnostic of futures pricing. When futures trade above spot, the basis is positive and the market is said to be in contango — the normal state for equity futures, because the cost of carrying a financed long position is positive when interest rates exceed dividend yield.

When futures trade below spot, the basis is negative and the market is in backwardation. For equity underlyings this typically signals one of a few conditions: an imminent large dividend or corporate action, heavy hedging or short interest that cannot be expressed cheaply in the cash market, difficulty or cost in borrowing the stock, or simply stressed sentiment in which participants pay to be short.

Basis converges to zero at expiry, because at settlement the futures price is set from the underlying's final settlement value. This convergence is mechanical and unavoidable, and it is what makes cash-and-carry arbitrage possible: an arbitrageur who buys spot and sells an overpriced future locks in the basis as a return, provided financing cost, transaction costs and margin funding are below the basis captured.

Basis is also the source of hedge imperfection. A portfolio hedged with index futures remains exposed to basis movement even if the index itself is perfectly tracked, because the futures leg and the cash leg can move apart temporarily. Rolling a hedge from one expiry to the next crystallises the difference between the two expiries' bases, called roll cost or roll yield.

## Cash-and-Carry and Reverse Arbitrage

Cash-and-carry arbitrage is the mechanism that keeps Indian equity futures close to their cost-of-carry fair value. If a futures contract trades meaningfully above fair value, an arbitrageur buys the underlying in the cash segment and simultaneously sells the equivalent quantity of futures. At expiry the futures settle at the underlying's value, the two legs cancel, and the arbitrageur retains the basis captured at entry less financing cost, brokerage, exchange fees, securities transaction tax, stamp duty and the opportunity cost of margin.

Reverse cash-and-carry is the mirror trade for futures trading below fair value: sell the underlying and buy the future. It is much harder to execute in India because sustained short selling in the cash segment is constrained. Institutional participants may borrow stock through the securities lending and borrowing mechanism, but availability and cost vary sharply by stock, and retail short selling in the cash segment is intraday only. This asymmetry is a structural reason equity futures can sit below fair value for longer than they can sit above it.

The economics require care. The apparent gross return of a basis spread must be reduced by every friction: two-sided transaction costs, taxes, the cost of funding cash-segment delivery, mark-to-market funding on the futures leg if the price moves against it before expiry, and dividend uncertainty for single stocks. Illustrative annualised basis returns quoted in market commentary are gross figures; net outcomes are materially lower. This section describes the mechanism and is not a recommendation to execute it.

## Mark-to-Market and Daily Settlement

Futures positions in India are marked to market daily, which means unrealised profit or loss is converted into an actual cash movement every trading day rather than accumulating until expiry. At the end of each session the clearing corporation computes a daily settlement price for each contract — conventionally derived from the volume-weighted average price of trades in the closing window, or from a theoretical price where trading is absent — and revalues every open position against it.

The mechanics are straightforward. On the day a position is opened, mark-to-market is computed against the trade price. On subsequent days it is computed against the previous day's settlement price. Gains are credited to the member's settlement account and losses are debited, with the pay-in and pay-out occurring on the following business day under the applicable settlement cycle. A trader whose position moves against them must fund the debit; failure to do so is a margin shortfall attracting penalty.

This daily cash cycle has two important consequences. First, a futures position consumes or generates cash continuously, so a strategy that is profitable at expiry can still fail if the holder cannot fund interim losses. Second, because losses are settled daily, the clearing corporation's exposure to any member is limited to roughly one day's move, which is what initial margin is calibrated to cover. Settlement price methodology, closing-window definitions and pay-in timings are exchange and clearing corporation rules that change; verify against the current exchange/SEBI circular before relying on this.

## Index Futures: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY

Index futures in this project's scope reference four benchmarks, and their contract characteristics differ enough to matter for position sizing. NIFTY futures use a lot size of 75 and reference the Nifty 50, a broad large-cap benchmark. BANKNIFTY futures use a lot size of 30 and reference a concentrated basket of banking stocks, which makes the index materially more volatile per unit of time than NIFTY. FINNIFTY uses a lot size of 65 and covers financial services more broadly, including non-bank lenders and insurers. MIDCPNIFTY uses a lot size of 120 and references a midcap select basket, with correspondingly higher idiosyncratic risk. All four lot sizes are illustrative; verify against the current exchange/SEBI circular before relying on this.

All index futures are cash-settled at expiry against the final settlement value of the index, which is conventionally derived from a volume-weighted average of the index over a defined closing window on expiry day rather than from a single closing print. Using an averaged window reduces the incentive and ability to manipulate settlement.

Monthly index futures expire on the last Thursday of the expiry month. Weekly expiry days used by this project apply principally to index options — NIFTY Thursday, BANKNIFTY Wednesday, FINNIFTY Tuesday, MIDCPNIFTY Monday — and the availability of weekly futures, as distinct from weekly options, is a product decision that has varied over time. Because notional value per lot differs greatly across these four contracts, a position expressed as "one lot" carries very different risk depending on which index it references.

## Single-Stock Futures and Physical Settlement

Single-stock futures in India are physically settled at expiry, and this is the most operationally consequential fact about them. An open long position in RELIANCE futures carried through expiry becomes an obligation to take delivery of 500 shares per lot against full payment of the settlement value; an open short becomes an obligation to deliver 500 shares. At an illustrative price of 2,900, one lot represents a 14,50,000-rupee delivery obligation, against which the trader may have deposited only a fraction as margin.

The consequences of ignoring this are severe and are covered in detail in the operational-controls document. In brief, brokers typically impose steeply increased margin requirements during expiry week on positions likely to go to delivery, may require full delivery margin, and often square off positions that clients have not squared off themselves ahead of an internal cut-off. A short position without shares creates a delivery failure, resolved through the exchange's auction or close-out mechanism at a price that can be substantially adverse to the defaulter.

Because of physical settlement, single-stock futures positions are commonly rolled rather than held into expiry. Rolling means buying back the near-month contract and selling the next-month contract simultaneously, paying or receiving the difference in bases. Rollover liquidity concentrates in the final three or four sessions before expiry.

The set of stocks with futures available is the exchange's F&O-eligible list, maintained against liquidity and market-capitalisation criteria under SEBI circulars on the F&O framework; stocks are added and removed periodically. Verify the current eligible list and the current physical-settlement rules against the exchange contract specification master before relying on this.

## Hedging with Futures: Ratios and Residual Risk

Hedging an equity exposure with futures requires converting the exposure into a number of contracts, and the standard tool is the beta-adjusted hedge ratio. If a portfolio has value V and beta β against the chosen index, and one index futures lot has notional value N, the number of lots required for a full hedge is (V × β) / N. A portfolio of 90 lakh rupees with a beta of 1.1 against NIFTY, hedged with futures at 24,000 and a lot size of 75 (notional 18,00,000 per lot), needs (90,00,000 × 1.1) / 18,00,000 = 5.5 lots. Because contracts trade in whole lots, the hedger must choose five or six and accept the rounding residual.

Residual risks persist even at the theoretically correct ratio. Beta is estimated from history and is unstable, particularly during stress when correlations shift. The portfolio's sector composition may diverge from the index, leaving unhedged sector exposure. Basis movement between futures and spot creates profit and loss that is not offset by the cash leg. And the hedge must be rolled at each expiry, incurring roll cost and execution slippage.

Cross-hedging — using NIFTY futures to hedge a midcap portfolio, for example — adds a further layer of mismatch, because the hedging index and the hedged assets can diverge for extended periods. Practitioners describe the choice of hedging instrument, ratio and rebalancing frequency as a trade-off between hedge precision and transaction cost. This section describes hedge construction mechanics only and does not recommend hedging or not hedging any particular exposure.

## Calendar Spreads and Rollovers

A calendar spread in equity futures is the simultaneous purchase of one expiry and sale of another expiry of the same underlying, and it isolates the difference between the two contracts' bases rather than the direction of the underlying. Long the near month and short the far month profits if the near-far differential narrows; the reverse profits if it widens. Because both legs reference the same underlying, the directional exposure largely cancels, and the position's risk is concentrated in carry, expected dividends and financing conditions.

Rollover is the specific calendar spread that traders execute for maintenance rather than for speculation: closing the expiring contract and opening the same position in the next expiry. Exchanges support spread orders that execute both legs together at a specified differential, which removes the leg risk of trying to trade them separately in a moving market. Rollover activity peaks in the last three to five sessions before expiry, and the aggregate rollover percentage — the share of open interest carried to the next series — is widely reported as an activity statistic.

Margining treats a calendar spread more favourably than two outright positions, because the offsetting nature of the legs reduces the portfolio's scenario loss. However the offset is not complete, and the margin benefit typically shrinks as the near leg approaches expiry, since the two contracts stop moving together. Illustrative spread margin treatments and the point at which the benefit is withdrawn are set by the clearing corporation and revised; verify against the current exchange/SEBI circular before relying on this.

## Price Bands, Freeze Limits and Circuit Filters

Price bands and quantity freezes are exchange-imposed constraints that shape how futures orders behave in fast markets, and encountering them unexpectedly is a common source of failed execution. Equity derivatives contracts operate within a dynamic price range around a reference price rather than a hard daily circuit; orders priced outside the operating range are rejected, and the range may be widened by the exchange in a defined process when genuine trading interest exists beyond it.

Quantity freeze limits cap the size of a single order. An order exceeding the freeze quantity for a contract is not automatically rejected but is held for exchange confirmation, which introduces delay and uncertainty. Traders needing large size therefore slice orders below the freeze threshold, which is one reason large positions are built through many small orders rather than one block.

In the underlying cash market, individual securities carry circuit filters, and index-level circuit breakers can halt trading market-wide at defined percentage moves, with halt durations depending on the level breached and the time of day. A market-wide halt suspends derivatives trading too, which means a derivatives position can become unmanageable precisely when it most needs managing — a risk that leveraged traders should account for in position sizing rather than assume away.

All of these thresholds — operating range percentages, freeze quantities, circuit filter levels and halt durations — are exchange parameters revised from time to time; verify against the current exchange/SEBI circular before relying on this. Nothing in this document constitutes investment advice; it describes contract mechanics only.
