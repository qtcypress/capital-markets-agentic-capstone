---
doc_id: KB-01
title: Equity Derivatives Basics
category: derivatives
last_reviewed: 2026-08-15
authority: educational
---

# Equity Derivatives Basics

## What an Equity Derivative Is

An equity derivative is a financial contract whose value is derived from an underlying equity asset — either a single listed share such as RELIANCE or TCS, or an equity index such as NIFTY 50 or BANKNIFTY. The derivative itself confers no ownership of the underlying shares, no voting rights and no automatic entitlement to dividends. What it confers is a contractual claim whose payoff is computed by reference to the price of the underlying at some future date or over some future period.

In the Indian market, exchange-traded equity derivatives are standardised contracts listed on recognised stock exchanges, principally the National Stock Exchange (NSE) and the BSE. Standardisation means the exchange, not the two counterparties, fixes the contract size (the lot size), the expiry date, the strike interval for options, the tick size and the settlement mechanism. Traders negotiate only price and quantity in lots.

Two broad families dominate: futures, which are firm obligations to transact at a fixed price on a fixed date, and options, which grant a right without a symmetric obligation on the buyer. Both are cleared through a clearing corporation that becomes the central counterparty to every trade, which is why an exchange-traded derivative carries clearing-house credit risk rather than the credit risk of the person on the other side of the screen. This central counterparty structure, backed by margining, is the single most important structural difference between exchange-traded and over-the-counter derivatives.

## Why Derivatives Exist: Hedging, Speculation and Arbitrage

Equity derivatives exist because three distinct economic motives converge on the same instruments, and the presence of all three is what makes the market liquid enough to function. The first motive is hedging. A holder of a large cash equity portfolio faces the risk that the market falls before they can or wish to sell. Rather than liquidating, the holder can take an offsetting position in index futures or index options, so that a fall in the portfolio is partially compensated by a gain in the derivative. The hedge is rarely exact, because the portfolio's composition differs from the index — the residual is called basis risk or tracking error.

The second motive is speculation, meaning the deliberate assumption of price risk in the expectation of a return. Derivatives are attractive here because they are leveraged: a margin deposit of a fraction of the contract's notional value controls the full notional exposure. Leverage magnifies both gains and losses, and the same margin mechanism that enables it also enforces daily recognition of losses.

The third motive is arbitrage — exploiting temporary inconsistencies between the derivative price and the price implied by the underlying, interest rates and time. Arbitrage activity is what keeps futures prices tethered to the cost-of-carry relationship and keeps option prices consistent with put-call parity. This document describes these mechanics only; nothing here is a recommendation to take any position.

## Futures Versus Options: The Core Distinction

Futures and options differ in the symmetry of obligation, and understanding this asymmetry is the foundation of everything else in equity derivatives. A futures contract binds both parties. The buyer of a NIFTY future is obliged to settle at the agreed futures price on expiry, whether the index has risen or fallen; the seller is equally obliged. The payoff is linear: every index point of movement produces a proportional gain to one side and an equal loss to the other. Because the obligation is symmetric, no premium changes hands at inception — only margin is deposited by both sides.

An option splits the obligation. The buyer pays a premium up front and acquires a right: a call buyer may buy the underlying at the strike, a put buyer may sell at the strike. The buyer is never compelled to exercise a right that is worthless, so the buyer's maximum loss is the premium paid. The seller, or writer, receives the premium and takes on the corresponding obligation, which can produce losses far exceeding the premium received. This is why option buyers post no margin beyond the premium, while option writers post margin comparable to a futures position.

The practical consequence is that futures produce a symmetric, linear risk profile, while options produce asymmetric, non-linear profiles that can be combined into a very wide range of payoff shapes.

## Underlyings: Indices and Single Stocks

Indian equity derivatives are written on two categories of underlying, and they behave quite differently in settlement and risk. Index derivatives reference a basket — NIFTY 50, BANKNIFTY (the Nifty Bank index), FINNIFTY (the Nifty Financial Services index) and MIDCPNIFTY (the Nifty Midcap Select index) are the principal contracts in this project's scope. Index contracts are cash-settled: no shares change hands at expiry, and the difference between the contract price and the final settlement value of the index is exchanged in cash.

Single-stock derivatives reference one company's shares. The set of eligible stocks is not open-ended; the exchange maintains an F&O-eligible list based on liquidity and market-capitalisation criteria set out in SEBI circulars on the F&O framework, and stocks enter and exit the list periodically. Single-stock futures and options in India are physically settled at expiry, meaning open in-the-money positions result in actual delivery or receipt of shares against full payment. This makes expiry-week management of single-stock positions operationally heavier than index positions.

Lot sizes used consistently throughout this knowledge base are illustrative: NIFTY 75, BANKNIFTY 30, FINNIFTY 65, MIDCPNIFTY 120, RELIANCE 500, TCS 175, INFY 400, HDFCBANK 550, ICICIBANK 700, SBIN 750, ITC 1600, AXISBANK 625. Lot sizes are revised by the exchange from time to time; verify against the current exchange/SEBI circular before relying on this.

## Contract Notation and Lot Sizes

Equity derivative contracts are identified by a compact symbol that encodes underlying, expiry, and — for options — strike and option type. A typical index option symbol reads as underlying, then expiry date, then strike, then CE for a call or PE for a put; for example a NIFTY contract expiring on a given Thursday at strike 24500 as a call would be written in the form NIFTY<expiry>24500CE. Futures carry no strike or option-type suffix and are commonly written with the expiry month, such as NIFTY<month>FUT.

The lot size converts a quoted price into money. Quoted prices for index options are per unit of index; multiplying by the lot size gives the rupee value of one contract. If a NIFTY call is quoted at 120 and the lot size is 75, one lot costs 120 × 75 = 9,000 rupees in premium. If a RELIANCE future is quoted at 2,900 and the lot size is 500, the notional value of one lot is 14,50,000 rupees, even though the margin deposited will be a fraction of that.

Orders must be placed in whole multiples of the lot size; there is no partial-lot trading in Indian exchange-traded derivatives. When an exchange revises a lot size, existing open positions are adjusted so that economic exposure is preserved, and new contracts list at the new size. Because lot size changes alter the rupee value of a one-point move, position-sizing logic in any trading system must read the current lot size from the exchange contract specification master rather than hard-coding it.

## Leverage, Notional Value and Margin Intuition

Leverage in equity derivatives arises because a trader controls a large notional exposure with a comparatively small margin deposit. Notional value is contract price multiplied by lot size multiplied by number of lots; it is the economic size of the position, not the cash required to hold it. Margin is the good-faith deposit the clearing corporation demands to cover a plausible one-day adverse move.

As an illustration, if a BANKNIFTY future trades at 52,000 with a lot size of 30, one lot has a notional value of 15,60,000 rupees. If the total initial margin requirement were roughly 12 to 15 percent of notional, the deposit would be in the region of 1.9 to 2.3 lakh rupees. These percentages move with volatility and with regulatory changes; verify against the current exchange/SEBI circular before relying on this.

The intuition that matters is the ratio: at roughly seven-to-one effective leverage, a one percent adverse move in the underlying consumes about seven percent of the margin deposited. A five percent adverse move can consume a third or more of the deposit and trigger a margin call. Leverage does not change the probability of a market move; it changes how much of a trader's capital that move touches. Any risk framework must size positions against notional exposure and worst-case scenario loss, not against margin alone.

## Long and Short Positions and What They Mean

A long position in an equity derivative is one that gains when the referenced quantity rises, and a short position is one that gains when it falls — but the phrase needs care because in options the direction refers to the option contract, not necessarily the underlying. Long a NIFTY future means the trader is obliged to buy at the futures price and profits if the index settles higher. Short a NIFTY future is the mirror image.

In options, "long" always means the contract has been bought and the premium paid, and "short" always means the contract has been sold and the premium received. So a long put is a purchased put: it is bought, the buyer pays premium, and it gains when the underlying falls. A short call is a sold call: premium is received, and it loses as the underlying rises. Confusing "long a put" with a bullish position is one of the most common beginner errors.

Shorting a derivative requires no borrowing of shares, unlike shorting in the cash segment. A trader can open a fresh short in a futures or options contract simply by selling it, because the contract is created at the moment of trade rather than transferred from an existing holder. Open interest — the count of contracts outstanding — therefore rises when a new buyer and a new seller transact, and falls when both sides are closing.

## Open Interest, Volume and Contract Life Cycle

Open interest and volume are two distinct measures of derivative activity, and conflating them produces bad inference. Volume counts contracts traded during a session and resets every day. Open interest counts contracts that remain open at the end of the session and carries forward; it rises only when a new long and a new short are created together, falls when a long and a short both close, and is unchanged when a position merely transfers from one holder to another.

The life cycle of a contract begins when the exchange introduces it. Index and stock contracts are typically introduced for near, next and far monthly expiries, with weekly expiries introduced for index contracts on a rolling basis. On introduction, open interest is zero. Through the contract's life, open interest builds as participants take positions, then decays into expiry as positions are closed or rolled to the next series.

Rolling over means closing the near-expiry position and simultaneously opening the equivalent position in the next expiry. Rollover activity is visible as open interest falling in the expiring series while rising in the next. On the final day, all remaining open positions must be settled by the exchange's settlement mechanism, and the contract ceases to exist. Because contract availability, the number of weekly expiries listed and the strike ranges offered are set by the exchange and revised periodically, always read the exchange contract specification master for the live position.

## The Clearing Corporation and Novation

The clearing corporation is the institution that makes exchange-traded equity derivatives creditworthy, and its central mechanism is novation. When a buyer and seller match on the exchange, the original bilateral contract is legally replaced by two contracts: one between the buyer and the clearing corporation, and one between the clearing corporation and the seller. The clearing corporation becomes buyer to every seller and seller to every buyer. Neither original party has any residual exposure to the other's creditworthiness.

To make that guarantee credible, the clearing corporation collects margins from clearing members, marks positions to market daily, maintains a settlement guarantee fund, and enforces a default waterfall specifying the order in which resources are consumed if a member fails. Clearing members in turn collect margin from trading members, who collect from clients. A client's position is thus supported by a chain of collateral, and shortfalls anywhere in the chain propagate quickly as margin calls.

Client-level segregation and reporting requirements mean that client collateral is identified and, in principle, protected from being used to cover another client's default. The practical consequence for a trader is that margin is not optional and cannot be negotiated: it is a system requirement enforced intraday. Details of margin computation, collateral eligibility and haircuts are set by the clearing corporation and SEBI and change over time; verify against the current exchange/SEBI circular before relying on this.

## Market Segments and Trading Hours

The Indian equity derivatives market operates as a distinct segment alongside the cash equity segment, with its own membership, margining and settlement arrangements, though prices are tightly linked. Normal trading in the equity derivatives segment runs on business days from the morning open to the afternoon close, in line with the cash market session, with a pre-open mechanism applying to the cash segment and specified derivative arrangements around the open and close. Exchanges have also operated extended-hours or evening sessions in certain segments at various times.

Trading holidays follow the exchange calendar, which includes national holidays and occasional special sessions such as the ceremonial Muhurat trading session. Session timings, extended-hours arrangements and holiday calendars are exchange decisions revised annually or more often; verify against the current exchange/SEBI circular before relying on this.

Within the segment, contracts are grouped by underlying and expiry. Index options dominate turnover by contract count, while single-stock futures and options carry a substantial share of notional turnover. Liquidity concentrates heavily in the near expiry and in strikes near the prevailing spot level; far strikes and far expiries can be materially wider in spread and thinner in depth. Any execution logic should therefore treat liquidity as a variable of strike distance and time-to-expiry rather than assuming uniform tradability across a contract chain.

## Risk Vocabulary Every Participant Needs

Equity derivatives carry a specific vocabulary of risk that recurs throughout this knowledge base, and defining it once at the basics level prevents confusion later. Market risk is the risk of loss from movement in the underlying price; for options it decomposes into directional risk, volatility risk and time decay. Basis risk is the risk that a hedge and the hedged item move differently, for example because a stock portfolio does not track NIFTY exactly. Liquidity risk is the risk that a position cannot be closed near the last traded price because depth is absent — acute in far strikes and in the final minutes before expiry.

Leverage risk is the risk that losses, magnified by notional exposure, exhaust deposited margin faster than the trader can respond. Assignment risk applies to option writers: a short option may be exercised against the writer, converting a premium position into an underlying obligation. Delivery risk applies specifically to single-stock F&O in India, where an in-the-money position carried to expiry becomes a physical delivery obligation requiring shares or full cash.

Operational risk covers everything that goes wrong outside the market itself: mistyped orders, wrong symbols, missed cut-offs, failed margin funding. Because operational failures in a leveraged, deadline-driven market can cost more than adverse price moves, they are treated as a first-class category in this knowledge base rather than an afterthought. Nothing in this document constitutes investment advice; it describes mechanics only.
