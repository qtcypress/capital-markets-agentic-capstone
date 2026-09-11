---
doc_id: KB-10
title: Risk Management and Position Limits
category: risk
last_reviewed: 2026-08-15
authority: regulatory-summary
---

# Risk Management and Position Limits

## Scope and Status of This Document

This document is an educational summary of risk management arrangements and position limit concepts in the Indian equity derivatives market, and it is not legal advice, investment advice or a statement of current regulation. Answers derived from this document should be presented as educational summaries only, never as compliance determinations or trading recommendations.

Every quantitative figure here is illustrative. Position limits, market-wide limits, margin percentages, ban thresholds and concentration norms are set through SEBI circulars on the F&O framework and exchange rulebooks and are revised regularly, sometimes at short notice. Verify against the current exchange/SEBI circular before relying on this. No circular numbers or dates are cited, because inventing them would create false precision.

The document covers two related but distinct subjects. The first is the market-level risk architecture — the limits and controls that exchanges, clearing corporations and the regulator impose to keep any single participant's exposure from threatening settlement integrity. The second is participant-level risk management — the position sizing, loss limits, scenario analysis and monitoring that an individual trader or firm applies to its own book.

The two interact. A participant who ignores its own risk management will eventually collide with the market-level limits, usually through a margin shortfall or a forced square-off, and a participant who understands the market-level architecture can anticipate constraints such as ban periods and expiry-week margin escalation before they bite. Neither substitutes for professional advice appropriate to the reader's circumstances.

## Why Position Limits Exist

Position limits exist to cap the concentration of derivative exposure that any single participant or the market as a whole may build in one underlying, and their purpose is systemic rather than paternalistic. Three concerns drive them.

The first is settlement integrity. The clearing corporation guarantees every trade, and a very large position held by one participant creates a concentrated default exposure. If that participant fails, the clearing corporation must close out a position too large to liquidate without moving the market, which converts a member default into a market-wide event.

The second is manipulation capacity. A participant holding derivative positions large relative to an underlying's free float or traded volume has both the incentive and potentially the means to influence the underlying's price, particularly around settlement. Limiting position size relative to the underlying's size limits that capacity.

The third is orderly market functioning. Derivative open interest far in excess of what the cash market can absorb creates the conditions for a squeeze, in which participants needing to close positions cannot do so at reasonable prices, and for disorderly physical settlement in single-stock contracts.

The limits are therefore expressed relative to the underlying's size — free-float market capitalisation, number of shares outstanding, or traded volume — rather than as fixed rupee amounts. They apply at several levels simultaneously: client, trading member, and market-wide. All levels must be satisfied, and the binding constraint is whichever is reached first. This is an educational description of purpose; specific limits are illustrative and change.

## Client-Level and Trading-Member Position Limits

Client-level position limits cap the derivative exposure a single client may hold in one underlying, and they are the limit most individual traders encounter. For index derivatives, the client-level limit is conventionally expressed as the higher of a fixed rupee amount of notional exposure or a percentage of total open interest in that index's derivatives, computed across futures and options on a delta-equivalent or notional basis depending on the applicable methodology. Illustrative constructions have used figures in the hundreds of crores of rupees or a low single-digit percentage of open interest.

For single-stock derivatives, the client-level limit is conventionally expressed as a percentage of the market-wide position limit for that stock, with an illustrative figure in the region of five percent, subject to a floor expressed in rupee terms for less liquid stocks.

Trading-member limits cap the aggregate exposure of all clients of one member plus the member's proprietary positions, and they are expressed similarly — a percentage of open interest or of the market-wide limit, whichever construction applies to the product.

Institutional participants, including registered foreign portfolio investors and mutual funds, are subject to their own limit structures, in some cases differentiated by whether the position is hedging an underlying cash holding.

The practical consequence for a large individual trader is that limits can bind before capital does, particularly in less liquid single-stock contracts where the market-wide limit itself is small. Systems should monitor utilisation as a percentage of the applicable limit, not merely absolute position size. All figures illustrative; verify against the current exchange/SEBI circular before relying on this. This is an educational summary and not a compliance determination.

## Market-Wide Position Limits and the Ban Period

Market-wide position limit, commonly abbreviated MWPL, is the cap on aggregate open interest across all participants in the derivatives of a single stock, and it is the mechanism behind the F&O ban period that Indian traders encounter regularly. The limit is conventionally computed from the stock's free-float shares — an illustrative construction uses a percentage of free float, subject to a floor — and it is recomputed periodically as free float changes.

The exchange publishes each stock's MWPL utilisation. When aggregate open interest across all participants exceeds a defined threshold of the MWPL — an illustrative threshold of ninety-five percent — the stock enters a ban period. During a ban, participants may not increase open interest: they may only place orders that reduce their existing positions. Opening a new position, or adding to an existing one, is rejected and attracts a penalty if executed.

The ban is lifted when aggregate open interest falls back below a lower threshold, and the exchange announces entry and exit. Bans typically last from one session to several, and a stock can enter and exit repeatedly.

The operational consequences are significant and often surprising. A trader holding a spread cannot roll it during a ban, because rolling requires opening a position in the next expiry. A hedger cannot add protection. A strategy that requires adjusting a position is stuck with the position it has. And because a ban is announced based on the previous session's data, a trader can begin a session unaware that a planned trade is now prohibited.

Thresholds, computation methods and penalty structures are illustrative and revised; verify against the current exchange/SEBI circular before relying on this.

## Scenario Analysis and Stress Testing a Derivatives Book

Scenario analysis is the practice of computing a portfolio's profit and loss across a grid of hypothetical market outcomes, and for options books it is more reliable than any Greek-based approximation. The reason is mathematical: Greeks are local derivatives, and option payoffs are non-linear, so a first-order estimate diverges from reality precisely in the large moves that matter for risk.

A practical grid varies two dimensions at minimum. The underlying price is varied across a range wide enough to include implausible outcomes — illustratively minus ten percent to plus ten percent in one percent steps for an index book, wider for single stocks. Implied volatility is varied across a range that reflects observed history, illustratively minus thirty to plus fifty percent relative change, with the asymmetry reflecting the tendency of volatility to spike upward. A third dimension, time, matters for short-dated books: revalue at today, at tomorrow's open and at expiry.

The output is a table of profit and loss values, and the risk measure is the worst cell, not the cell nearest current conditions. A short strangle that shows modest negative gamma in Greek terms may show a loss many multiples of the premium collected in the corner cells, which is the honest statement of its risk.

Stress testing extends the grid with historically motivated shocks: a single-day index gap of the magnitude seen in past crises, a volatility spike of the magnitude seen around major events, a simultaneous move in the underlying and expansion of volatility, and a liquidity assumption in which positions cannot be closed at all for one session.

Because SPAN margining itself uses a scenario grid, a book whose worst scenario loss is large will also attract large margin — the two constraints move together. This describes methodology only and is not investment advice.

## Position Sizing and Capital Allocation

Position sizing in a leveraged derivatives book is the discipline of choosing exposure relative to capital, and the central error it prevents is sizing against margin rather than against risk. Margin is the deposit required to hold a position; risk is the loss the position can produce. For a naked short option the two are unrelated in magnitude, because margin covers a plausible one-day move while the position's loss is unbounded.

Sound practice sizes against a defined worst-case scenario loss drawn from the scenario grid described above, then against a limit expressed as a percentage of total capital. Illustratively, a firm might cap the worst-case single-day loss of the entire derivatives book at a low single-digit percentage of capital, and cap the worst-case loss attributable to any one underlying at a fraction of that.

Notional exposure is a second constraint, distinct from scenario loss. One lot of NIFTY futures at 24,000 with lot size 75 carries 18,00,000 rupees of notional exposure; a trader with 5 lakh of capital holding three such lots has notional exposure over ten times capital, which no scenario limit expressed in comfortable terms would permit.

Concentration limits complete the framework: a cap on exposure to a single underlying, a single expiry and a single strategy type, so that one adverse event cannot exhaust capital. Books that were short options across several correlated underlyings have repeatedly discovered that diversification by symbol is not diversification by risk factor.

Every figure here is illustrative and is offered to show the shape of a sizing framework, not as a recommendation for any person. Nothing in this section is investment advice, and no allocation described here is suitable for any particular reader.

## Loss Limits, Kill Switches and Automated Controls

Loss limits and automated controls are the mechanisms that convert a risk policy into something that actually stops trading, and their value lies in operating without requiring a decision under stress. Human judgement degrades exactly when a book is losing quickly, which is why pre-committed automated limits outperform intention.

A layered structure is standard. A per-order control checks price against the last traded price and rejects orders outside a tolerance band, and checks quantity and order value against configured maxima — the fat-finger defence. A per-position control caps the size of any single contract position and blocks orders that would exceed it. A per-underlying control caps aggregate exposure. A book-level control monitors intraday realised plus unrealised profit and loss against a daily loss limit and blocks new risk-increasing orders when breached. A kill switch cancels all open orders and, if configured, squares off positions.

For algorithmic trading, these controls are not merely prudent but required: the Indian framework mandates broker-level pre-trade risk controls and kill-switch capability for approved algorithms, with order-to-trade ratio monitoring layered on top.

Two design points matter. Controls must be enforced server-side or at the broker, not only in the client application, because a client-side check fails when the application misbehaves. And the daily loss limit must block risk-increasing orders while permitting risk-reducing ones, since a limit that blocks all trading traps the trader in the losing position.

Specific tolerance bands, limit levels and regulatory requirements for algorithmic controls are illustrative and revised; verify against the current exchange/SEBI circular before relying on this. This is an educational summary, not compliance or investment advice.

## Liquidity Risk in Derivatives Positions

Liquidity risk in equity derivatives is the risk that a position cannot be closed at a price near its theoretical or last traded value, and it is systematically underestimated because it is invisible until it matters. Liquidity in an option chain is not uniform: it concentrates at and near the at-the-money strike in the nearest expiry and decays sharply with distance from spot and with time to expiry.

Three specific exposures recur. Far out-of-the-money strikes may show a last traded price from hours earlier with no live bid, which means the position cannot be sold at all in that moment regardless of what a valuation model says. Far expiries in single-stock options may have no continuous two-way quote, so entry and exit both require accepting a wide spread. And liquidity evaporates precisely under stress: spreads widen and depth thins during sharp moves, so the cost of closing is highest when the need is greatest.

Compounding factors specific to India include quantity freeze limits, which prevent exiting a large position in a single order; price operating ranges, which reject orders priced beyond the current band during fast moves; F&O ban periods, which prohibit position-increasing orders and therefore prevent hedging; and market-wide circuit breakers, which halt derivatives trading entirely.

The practical response is to treat liquidity as a position-sizing input rather than an execution detail. Size positions so they can be exited across several orders within a reasonable fraction of typical volume in that contract; prefer strikes and expiries with genuine two-way depth; and assume in stress scenarios that closing costs several ticks more than the current spread suggests. This describes risk mechanics only and recommends no position.

## Counterparty and Broker Risk

Counterparty risk in exchange-traded equity derivatives is largely eliminated at the trade level by novation, but it is not eliminated entirely, and understanding where it remains is part of a complete risk picture. After novation the clearing corporation is the counterparty to every position, so the creditworthiness of the person on the other side of the screen is irrelevant. The clearing corporation's own resilience is supported by margin, a settlement guarantee fund and a default waterfall.

The residual exposure is to the intermediary chain. A client's positions and collateral sit with a trading member, which clears through a clearing member. If a member fails, the client's positions and collateral become entangled in the default process. Client-level position and collateral reporting, segregation requirements, the margin pledge mechanism that keeps securities in the client's own demat account, and upstreaming of client funds to the clearing corporation all exist to reduce this exposure, but they reduce rather than remove it.

Operational broker risk is distinct and more commonly encountered. Brokers impose their own margin requirements above the exchange minimum, apply their own expiry-week restrictions on single-stock positions, and reserve the right to square off client positions unilaterally when margin is short or when a physically settled position approaches an internal cut-off. A forced square-off at an adverse price is a real loss caused by the broker relationship rather than by the market.

Practical mitigations are to understand the broker's margin and square-off policy in writing, to maintain a margin buffer above the requirement, and to avoid reliance on discretionary broker forbearance. This is an educational summary and not advice about any intermediary.

## Risk Reporting and Monitoring Practice

Risk reporting for a derivatives book must be structured around what can actually go wrong, and a report that lists only positions and unrealised profit and loss omits most of the useful information. A workable daily report has five sections.

Exposure reports net delta expressed in rupees per one percent move, net gamma as the rupee change in that delta per one percent move, theta in rupees per day, and vega bucketed by expiry rather than summed, since the term structure does not move uniformly. Aggregation across underlyings must use rupee terms rather than raw index points.

Scenario reports the profit-and-loss grid across underlying price and volatility shocks, with the worst cell highlighted as the headline risk number.

Margin reports the current requirement, the peak intraday requirement, available collateral split between cash and pledged securities, the cash-equivalent proportion against its minimum, and the resulting buffer.

Expiry reports every position with its expiry date, flags contracts expiring within a configured number of sessions, and separately flags physically settled single-stock positions with their delivery value in rupees and shares computed at current prices.

Limits reports utilisation against client-level position limits, against market-wide position limit for each single stock held, and against internal concentration and loss limits, each as a percentage rather than an absolute.

Monitoring frequency should match the risk regime: end-of-day suffices for a book of monthly index positions, while a book holding expiry-day options requires intraday monitoring, since gamma and margin both move quickly. Answers derived from this document are educational summaries, not legal, regulatory or investment advice, and no figure here is a current regulatory requirement.
