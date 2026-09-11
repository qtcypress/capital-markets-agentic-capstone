---
doc_id: KB-11
title: Market Microstructure and Order Types
category: operations
last_reviewed: 2026-08-15
authority: educational
---

# Market Microstructure and Order Types

## The Order Book and Price-Time Priority

The order book is the central data structure of the Indian equity derivatives market: a list of resting buy orders ranked from highest price down and resting sell orders ranked from lowest price up, with the best bid and best offer at the top forming the spread. The exchange's matching engine executes trades by applying price-time priority — the best price is served first, and among orders at the same price the one entered earlier is served first.

Price-time priority has direct consequences for execution. An order that improves on the existing best price goes to the front of the queue. An order at the existing best price joins the back of the queue at that level and executes only after all earlier orders there are filled. Modifying an order's price or increasing its quantity generally forfeits time priority, which is why traders reduce rather than increase quantity when adjusting a resting order they want to keep near the front.

The book is anonymous in Indian markets: participants see aggregated quantity at each price level but not the identity of the order's owner. Depth displayed is conventionally the best five price levels on each side, and total buy and sell quantity is shown separately.

Liquidity in a derivatives order book is highly uneven. For an index option chain, the at-the-money strike in the near expiry typically shows tight spreads and substantial depth at multiple levels, while a strike several hundred points away may show a single order on each side with a spread of several rupees, and a deep out-of-the-money strike may show no bid at all. Reading depth rather than only the last traded price is therefore essential before sizing an order.

## Market Orders and Their Risks

A market order instructs the exchange to execute immediately at the best available prices in the book, without specifying a price, and it guarantees execution but not price. In a deep, tight book a market order fills close to the displayed best price. In a thin book it walks up or down the levels, consuming each until the full quantity is filled, at an average price that can be far from the level the trader saw.

The risk is acute in derivatives because option books are frequently thin. A market buy order for 20 lots of a NIFTY option showing a best offer of 95 with only 3 lots available may fill the remaining 17 lots at 97, 101, 108 and higher, producing an average materially above the quote. At a lot size of 75, each rupee of slippage is 1,500 rupees across 20 lots.

The extreme case is the freak trade: a market order meeting a near-empty book executes at an absurd price — a deep out-of-the-money option quoted at a few paise filling at tens or hundreds of rupees. This is a recurring phenomenon on Indian expiry days and is covered in the operational-controls document.

Indian exchanges apply protections that mitigate but do not eliminate the risk. Price operating ranges prevent execution outside a band around the reference price, which caps how far a market order can walk. Some brokers convert market orders into aggressive limit orders internally, or block market orders in illiquid contracts entirely.

The practical guidance is mechanical rather than advisory: in derivatives, especially in options away from the money and near expiry, limit orders bound the price paid while market orders do not.

## Limit Orders, Immediate-or-Cancel and Day Orders

A limit order specifies the worst acceptable price and executes only at that price or better, which makes it the default instrument of price control in derivatives trading. A limit buy at 95 will fill at 95 or lower and will never fill at 96. The trade-off is that execution is not guaranteed: if the market moves away, the order rests unfilled or is cancelled at the end of the session.

Validity attributes determine how long the order lives. A day order rests in the book until filled or until the session ends, at which point it lapses. An immediate-or-cancel order executes whatever quantity is available at the limit price or better at the instant of entry and cancels the remainder without resting — useful for taking displayed liquidity without leaving a footprint in the book. Some venues and brokers also support a fill-or-kill variant that requires the entire quantity or cancels completely.

Indian derivatives markets do not conventionally offer good-till-cancelled orders at the exchange level for derivatives; brokers may simulate multi-day orders by re-entering them, which is a broker feature rather than an exchange one, and the simulation can fail.

Two practical patterns are worth knowing. A limit order priced at or through the opposite side of the book behaves like a market order but with a hard price cap, which is the standard way to trade aggressively without unbounded slippage. And a limit order priced far from the market may be rejected outright if it falls outside the contract's price operating range, so a rejection is not always a sign of insufficient margin.

## Stop-Loss and Stop-Loss-Market Orders

A stop-loss order is a conditional order that becomes active only when the market reaches a specified trigger price, and it is the standard mechanism for pre-committing an exit. Until triggered it is not in the order book and cannot be executed; once the trigger condition is met it is released into the book as either a limit order or a market order depending on its type.

A stop-loss limit order specifies both a trigger price and a limit price. For a long position being protected, the trigger is set below the current price and the limit slightly below the trigger, so that when the market falls to the trigger the order becomes a sell limit. The risk is that a fast move gaps past the limit price, leaving the order unfilled and the position unprotected — the order triggered but could not execute.

A stop-loss market order specifies only a trigger and releases a market order when hit. It maximises the probability of execution and abandons control of price, so in a thin derivatives book it can fill far from the trigger.

The trade-off is unavoidable: stop-loss limit risks non-execution, stop-loss market risks bad execution. Neither guarantees a loss will be capped at the trigger level.

Two specifically derivative complications apply. Triggers based on option premium behave erratratically because premium is a non-linear function of the underlying — a small index move near expiry can move premium through a wide range instantly. And on a gap opening, a stop set within the gap is triggered immediately at the open price with no opportunity to execute nearer the trigger. Stop-loss orders are mechanisms, not guarantees, and nothing here recommends any particular use of them.

## Cover Orders, Bracket Orders and Broker Products

Cover orders and bracket orders are broker-constructed product wrappers rather than exchange order types, and distinguishing them from native exchange functionality matters because their behaviour depends on the broker's implementation. A cover order combines an entry order with a compulsory stop-loss placed simultaneously, so the position can never exist without a protective order attached. Because the maximum loss is bounded by construction, brokers historically offered higher intraday leverage on cover orders, though leverage available has been constrained by the peak margin framework.

A bracket order extends this with three legs: an entry, a stop-loss and a target, with the stop and target linked so that execution of one cancels the other. Some implementations add a trailing stop that moves the stop level as the position becomes profitable.

Three cautions apply. These products are intraday only in most implementations and are squared off automatically before the close, regardless of the trader's intent — a position expected to be carried can be closed without action by the trader. The stop-loss leg is subject to all the limitations described earlier, so a bracket order's stop can gap through and fill far from its level. And the linkage logic between legs is the broker's software, so a partial fill on the entry can leave the protective legs mis-sized if the implementation handles it poorly.

Additionally, brokers may withdraw these products in specific contracts, during expiry week, or in high-volatility conditions, which means a strategy dependent on them can become unexecutable. Product availability, leverage and automatic square-off timings are broker policies revised without notice; verify against your broker's policy and the current exchange/SEBI circular before relying on this.

## Bid-Ask Spread and Transaction Cost Components

The bid-ask spread is the difference between the best offer and the best bid, and it is the first and often largest component of the cost of trading a derivative. A trader who buys at the offer and sells at the bid pays the full spread as a round-trip cost, so a spread of one rupee on a NIFTY option is 75 rupees per lot per round trip at a lot size of 75.

Spread width varies systematically. It is tightest for at-the-money options in the nearest expiry, widens with distance from spot, widens with time to expiry in single-stock options, and widens sharply during fast moves and in the final minutes of an expiry session. Expressed as a percentage of premium, spreads on cheap far out-of-the-money options are enormous: a 0.50 bid against a 0.70 offer is a forty percent round-trip cost.

Beyond the spread, transaction costs comprise several layers. Brokerage is charged per order or as a percentage, and multi-leg strategies incur it per leg. Securities transaction tax applies on specified derivative transactions at rates that differ between futures and options and, for options, between premium and exercised value. Exchange transaction charges are levied on turnover, with different rates for futures and options. SEBI turnover fees apply. Stamp duty applies on the buy side. Goods and services tax applies on brokerage and on exchange and SEBI charges.

Then comes slippage — the difference between the price expected and the price achieved — and market impact for larger orders. All statutory rates change; verify against the current exchange/SEBI circular before relying on this. The taxation document treats securities transaction tax in more detail.

## Slippage, Market Impact and Execution Quality

Slippage is the difference between the price a trader intended and the price actually achieved, and in derivatives it is frequently larger than brokerage and statutory charges combined. It arises from three distinct sources, and separating them helps in reducing it.

Latency slippage occurs because the market moves between the moment the trader decides and the moment the order reaches the matching engine. In fast markets, and especially in expiry-day options where premium moves rapidly, the quote seen on screen may be stale by the time an order arrives.

Spread slippage occurs because an aggressive order pays the spread. A trader who must transact immediately crosses from mid to offer or bid, which is a real cost even when the fill matches the displayed quote exactly.

Market impact occurs because a large order consumes multiple price levels and, beyond that, signals demand that causes other participants to adjust their quotes. Impact grows non-linearly with size relative to available depth. An order for a quantity comparable to the total displayed depth in a contract will move the price against itself substantially.

Reducing slippage is a matter of technique rather than aspiration: use limit orders to bound price, slice large orders into pieces sized against displayed depth and against the quantity freeze limit, prefer contracts and strikes with genuine two-way depth, avoid the first and last minutes of the session where spreads are widest, and use exchange-supported spread orders for multi-leg structures rather than legging in.

Measuring execution quality requires recording the mid-quote at decision time and comparing it with the achieved average price, aggregated over many orders. This describes execution mechanics only and is not investment advice.

## Trading Session Structure and Pre-Open

The trading session in the Indian equity derivatives segment runs on business days from the morning open to the afternoon close, aligned with the cash market session, and its structure shapes liquidity through the day. The cash segment operates a pre-open session in which orders are collected without matching and an equilibrium opening price is discovered through a call auction, after which continuous trading begins.

Derivatives trading begins with continuous matching at the open. Because the underlying's opening price emerges from the cash segment's call auction, derivative prices in the first minutes reflect the market's adjustment to that discovery, and spreads are typically at their widest of the day. Liquidity builds through the morning, often thins around midday, and increases again toward the close as positions are adjusted.

The closing period matters especially for derivatives. Daily settlement prices are computed from a closing window, and on expiry day the final settlement value is computed from an averaged window, so activity concentrates there. Traders who need a specific price should be aware that the last minutes carry both the highest volume and, frequently, the widest spreads in individual option strikes.

Exchanges have at various times operated extended or evening trading sessions in certain segments, and session timings, pre-open arrangements and closing-window definitions are exchange decisions revised periodically. Trading holidays follow the exchange calendar, which also includes occasional special sessions such as the ceremonial Muhurat session. Verify session timings and the holiday calendar against the current exchange/SEBI circular before relying on this.

## Circuit Breakers and Trading Halts

Circuit breakers are automatic trading halts triggered by defined percentage moves, and they matter to derivatives traders because a halt suspends the ability to manage a leveraged position. Two distinct mechanisms operate.

Individual security circuit filters apply in the cash segment, capping how far a single share's price may move from its previous close within a session. Shares with derivatives listed on them are typically subject to a wider band or a dynamic price band mechanism rather than a hard narrow filter, because a frozen underlying would make the derivative unpriceable.

Index-based market-wide circuit breakers halt trading across all segments — cash and derivatives — when a benchmark index moves by defined percentage thresholds. The framework uses three escalating thresholds, and the duration of the halt depends on which threshold was breached and at what time of day, with a breach later in the session producing a longer halt or closure for the remainder of the day. After a halt, trading resumes with a pre-open call auction.

In derivatives specifically, contracts operate within dynamic price operating ranges rather than hard circuits, and the exchange can widen a range through a defined process when genuine interest exists beyond it. An order priced outside the current range is rejected at entry.

The risk this creates is straightforward and often overlooked: a position that requires adjustment may be unmanageable during a halt, and a leveraged position can accumulate loss through the halt with no ability to close. Position sizing that assumes continuous access to the market is therefore optimistic. Threshold levels, halt durations and band mechanics are exchange parameters revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Market Makers, Liquidity Providers and Open Interest Data

Market makers and liquidity providers are participants who quote two-way prices in derivative contracts, and their presence or absence explains most of the variation in spread width across an option chain. Exchanges have operated liquidity enhancement schemes that incentivise members to maintain continuous two-way quotes with defined maximum spreads and minimum quantities in specified contracts, particularly in less active series.

Where such quoting exists, a contract shows a tight, continuous spread with reasonable depth. Where it does not, the book consists only of opportunistic orders from directional traders, which is why deep out-of-the-money strikes and far expiries can show no bid at all. A trader relying on being able to exit a position is implicitly relying on someone quoting the other side.

Open interest data published by the exchange is the other principal microstructure dataset. Open interest counts contracts outstanding at end of session; it increases only when a new long and new short are created together, decreases when both sides close, and is unchanged when a position merely transfers. Change in open interest is therefore the informative field for activity, while the level indicates accumulated positioning.

Market commentary routinely interprets open interest concentrations at particular strikes as support or resistance, and combines open interest change with price change to infer whether new longs or new shorts are driving a move. These are inferences by the reader, not mechanisms guaranteed by market structure, and this document makes no claim that any such interpretation predicts price. Nothing in this document is investment advice; it describes market mechanics and data definitions only.
