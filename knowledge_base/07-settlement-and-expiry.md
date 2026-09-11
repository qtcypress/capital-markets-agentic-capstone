---
doc_id: KB-07
title: Settlement and Expiry
category: operations
last_reviewed: 2026-08-15
authority: educational
---

# Settlement and Expiry

## The Expiry Calendar Used by This Project

The expiry calendar governs when every derivative contract terminates, and in the Indian index options market it is dense enough that a multi-index book faces an expiry on most trading days. The weekly expiry days used by this project are NIFTY on Thursday, BANKNIFTY on Wednesday, FINNIFTY on Tuesday and MIDCPNIFTY on Monday. Monthly expiry for all contracts, index and single-stock, is the last Thursday of the month.

Two adjustment rules apply. Where a scheduled expiry day is a trading holiday, expiry moves to the immediately preceding business day — so a Thursday expiry falling on a holiday becomes a Wednesday expiry. And in the week containing the monthly expiry, the weekly contract expiring on the same day as the monthly contract is generally the monthly contract itself rather than a separate weekly series.

Single-stock futures and options in India are listed on monthly expiries only, so single-stock positions face expiry once a month on the last Thursday, not weekly.

The assignment of weekdays to indices, the number of weekly expiries listed simultaneously, and indeed which indices carry weekly options at all are exchange product decisions that have been revised more than once, including consolidation of weekly expiries onto fewer underlyings. Any system that hard-codes an expiry weekday will eventually be wrong. Read expiry dates from the exchange contract specification master, and verify against the current exchange/SEBI circular before relying on this. Contract-level expiry dates, not weekday rules, should drive risk and settlement logic.

## Cash Settlement of Index Derivatives

Cash settlement is the mechanism by which all Indian index derivatives terminate: no basket of shares changes hands, and the difference between the contract's terms and the index's final settlement value is exchanged in money. This applies to NIFTY, BANKNIFTY, FINNIFTY and MIDCPNIFTY futures and options alike.

For an index future, final settlement computes the difference between the previous day's settlement price and the final settlement value, multiplied by lot size, and debits or credits it. For an index option, the clearing corporation exercises all in-the-money contracts automatically and settles their intrinsic value in cash. A NIFTY 24,000 call with a final settlement value of 24,180 settles at 180 per unit, or 13,500 rupees per lot at lot size 75, paid by the writer to the holder. Out-of-the-money options lapse with no cash flow.

The reason index contracts are cash-settled is practical: delivering a fifty-stock basket in exact index weights would be operationally infeasible at retail scale, and the index has no existence as a deliverable asset.

The consequence for traders is that index positions carry no delivery risk. An index option left to expire creates only a cash debit or credit, bounded by the intrinsic value. This is a materially lower operational risk than single-stock expiry, and it is a principal reason index options dominate retail derivative volume. Settlement obligations are debited and credited through the normal settlement cycle on the business day following expiry, subject to the applicable timetable.

## Final Settlement Price and the Closing Window

The final settlement price for index derivatives is not the last traded value of the index on expiry day; it is derived from the index's behaviour over a defined window near the close, and understanding this distinction matters for anyone holding positions into settlement. The conventional approach uses a volume-weighted average of the index computed over the last period of the expiry-day session — an illustrative half-hour window — rather than a single instantaneous print.

The rationale is manipulation resistance. A single closing print can be influenced by concentrated activity in a handful of constituent stocks in the final seconds, and because settlement of a very large open interest depends on that number, the incentive to influence it would be substantial. Averaging over a window across many prints and many constituents raises the cost of influence enormously.

For single-stock derivatives, the final settlement price is conventionally derived from the closing price of the underlying share in the cash segment on expiry day, computed under the cash market's own closing-price methodology, which itself uses a weighted average over a closing window.

The practical implication is uncertainty. A trader holding a near-the-money option on expiry afternoon cannot know whether it will finish in-the-money, because the determining number is an average that is still forming. An option that appears out-of-the-money at 15:15 may settle in-the-money, triggering assignment. This is why positions that must not be settled should be closed rather than left to the settlement calculation. Window definitions and methodologies are exchange rules revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Physical Settlement of Single-Stock Derivatives

Physical settlement is the mechanism by which all Indian single-stock futures and options terminate at expiry: open positions convert into actual obligations to deliver or receive shares against full payment. This is the single most operationally consequential difference between the stock and index segments.

The rules follow from position type. A long futures position becomes an obligation to take delivery of the contract quantity at the final settlement price. A short futures position becomes an obligation to deliver those shares. An in-the-money long call becomes an obligation to buy at the strike; an assigned short call, an obligation to deliver at the strike. An in-the-money long put becomes an obligation to sell at the strike; an assigned short put, an obligation to buy. Out-of-the-money options lapse and create no obligation.

The magnitudes are the point. One lot of RELIANCE at lot size 500 and an illustrative 2,900 rupees is a 14,50,000-rupee obligation. HDFCBANK at 550 shares and 1,650 rupees is about 9,07,500. ITC at 1600 shares and 450 rupees is 7,20,000. SBIN at 750 shares and 800 rupees is 6,00,000. A trader holding several lots on margin of a fraction of these values faces a funding requirement many times the margin posted.

Failure to deliver or to pay is a settlement default, resolved through the exchange's close-out or auction mechanism at a price set by the shortage procedure, which is deliberately unfavourable to the defaulting party. Delivery timetables, margin escalation schedules and close-out rules are exchange and clearing corporation rules revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Automatic Exercise and Do-Not-Exercise

Automatic exercise is the standard treatment of in-the-money options at expiry in India: the clearing corporation exercises them without any instruction from the holder. A holder of an in-the-money NIFTY call need do nothing to receive the intrinsic value, and a holder of an out-of-the-money option need do nothing either, because it simply lapses.

Automatic exercise is efficient for cash-settled index options, where the outcome is always a cash amount favourable to the holder. It is more complicated for physically settled single-stock options, because exercise generates a delivery obligation. A holder of a slightly in-the-money single-stock call may prefer not to exercise, since the intrinsic value gained can be smaller than the transaction costs, securities transaction tax on delivery and funding cost of taking delivery.

To address this, exchanges have at times operated a do-not-exercise facility, allowing holders of specified close-to-the-money physically settled options to instruct that the option not be exercised, within a defined window before the exercise cut-off. The facility's availability, the moneyness bands to which it applies and the instruction deadlines have been changed and at points withdrawn; verify against the current exchange/SEBI circular before relying on this.

The safer operational posture, independent of whether the facility exists, is to close unwanted single-stock option positions in the market rather than to rely on an exercise election. Closing is a trade the holder controls; a do-not-exercise instruction depends on a facility existing, on the option being within the eligible band, and on the instruction reaching the exchange before a cut-off.

## Expiry-Day Market Behaviour

Expiry-day behaviour in Indian index options is distinctive enough to be treated as its own regime rather than as an ordinary session, and the drivers are mechanical rather than sentimental. As time to expiry approaches zero, option value converges to the kinked payoff, which makes gamma extreme for strikes near spot and drives theta to its maximum rate. Vega collapses, so implied volatility levels stop mattering to premium.

Volume concentrates overwhelmingly in the expiring series and within it in strikes near spot. Premiums on at-the-money weekly options can move by large multiples within minutes on modest index moves, because the entire remaining value is a binary bet on the settlement average. Deep out-of-the-money strikes trade at a few paise and occasionally print at anomalous prices when a market order meets an empty book — the freak-trade phenomenon.

Delta hedging becomes unstable. A hedge computed at the open can be materially wrong by midday because charm and gamma are both large, and a hedger who rebalances mechanically may find each adjustment immediately stale. Short-gamma books face their largest single-day risk on expiry day, and their margin can expand at exactly the moment liquidity to close is thinnest.

Toward the close, the settlement window begins forming the number that determines every in-the-money outcome, and open interest at strikes near spot resolves to either full intrinsic value or zero. Bid-ask spreads on strikes bracketing spot frequently widen in the final minutes.

Because four indices expire on four different days under this project's convention, this regime recurs almost daily for a diversified book. Nothing here predicts price direction; it describes mechanical consequences of time decay.

## Settlement Cycles and Pay-In, Pay-Out

Settlement cycles define when money and securities actually move, and they matter because a derivatives trader's funding obligations are dated events, not abstractions. In the Indian derivatives segment, daily mark-to-market obligations arising from a session are settled through pay-in and pay-out on the following business day, and final settlement obligations arising at expiry are settled on the business day following expiry, subject to the applicable timetable.

Pay-in is the collection of funds from members with net obligations; pay-out is the distribution to members with net entitlements. Pay-in must complete before pay-out, and the clearing corporation enforces a deadline. A member that fails to meet pay-in triggers the default process, and the member's clients whose positions caused the shortfall bear the consequences through their own broker relationship.

Physical delivery settlement in single-stock derivatives operates through the cash segment's delivery mechanism, so shares and funds move on the cash market's settlement timetable following expiry. The Indian cash market has moved to shorter settlement cycles over time, and a shorter cycle compresses the window in which a trader can arrange shares or funds for a delivery obligation.

For a trader, the practical rules are that funds must be available in the trading account before the pay-in deadline rather than during the following session, that securities intended for delivery must be free and unpledged in the demat account before the delivery deadline, and that pledged collateral cannot generally be used to satisfy a delivery obligation without being unpledged first, which itself takes time. Settlement timetables and deadlines are exchange rules revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Rollover Mechanics and Timing

Rollover is the process of transferring an expiring derivatives position to the next expiry, and for single-stock positions it is the standard alternative to physical settlement. Mechanically it consists of closing the near-expiry contract and simultaneously opening the same position in the next expiry — buying back a short and selling the next month, or selling a long and buying the next month.

Rollover is not free. The price difference between the two expiries, the roll spread, reflects cost of carry over the additional period, expected dividends and prevailing demand. A long position rolling forward in a contango market pays the spread; the same position rolling in backwardation receives it. Illustratively, with RELIANCE near-month at 2,905 and next-month at 2,925, a long roller pays 20 rupees per share, or 10,000 rupees per lot at lot size 500.

Timing matters for execution quality. Rollover liquidity concentrates in the final three to five sessions before expiry, so rolling too early means trading a thinner next-month contract, while rolling on the final day means competing with everyone else and facing the widest spreads. Exchange-supported spread orders execute both legs at a specified differential and eliminate the risk of the market moving between two separately placed legs.

Rollover also interacts with margin. During the overlap when both legs exist, SPAN recognises the calendar spread and charges a spread charge rather than two outright margins, though the benefit typically narrows as the near leg approaches expiry. And a roll executed after a broker's internal expiry-week cut-off may be refused if the broker has already restricted new positions in the expiring series. Nothing here recommends rolling or not rolling any position.

## Expiry-Week Risk Management for Single-Stock Positions

Expiry week in single-stock derivatives concentrates several risks simultaneously, and managing it is largely a matter of acting early rather than reacting. The central fact is that physical settlement converts a margin-financed derivative into a full-value share transaction, so the funding requirement of an unchanged position can multiply within a few sessions.

Four pressures arrive together. Delivery margins escalate on a staged schedule through the final sessions. Brokers impose their own, usually earlier and stricter, requirements and may square off positions unilaterally at an internal cut-off. Liquidity in the expiring series thins as others roll or close, widening spreads precisely when closing becomes urgent. And options that are near the money face genuine uncertainty about whether they will be assigned, because settlement depends on a closing average not yet known.

The controls that address this are procedural. Maintain an inventory of all single-stock positions with their expiry dates and delivery values computed at current prices. Decide well before expiry week whether each position will be closed, rolled or delivered, and for delivery confirm that funds or unpledged shares will be available on the settlement date. Treat near-the-money short options as likely to be assigned rather than likely to lapse. Unpledge any securities intended for delivery early, since unpledging is not instantaneous.

For long option positions that are marginally in-the-money, closing in the market is usually preferable to relying on exercise, because the intrinsic value can be smaller than the combined cost of delivery, taxes and funding. Margin escalation schedules and broker cut-offs vary; verify against the current exchange/SEBI circular and your broker's policy before relying on this.

## Settlement Failures, Auctions and Close-Out

Settlement failure occurs when a party with a delivery obligation in physically settled single-stock derivatives cannot deliver the shares, or cannot fund the purchase, and the exchange resolves it through a defined shortage procedure rather than leaving the counterparty unpaid. The clearing corporation's guarantee means the non-defaulting side is made whole; the cost falls on the defaulter.

The traditional mechanism is an auction, in which the exchange invites offers to supply the undelivered shares, purchases them, delivers to the entitled party and charges the defaulter the auction price plus penalties. Where an auction cannot source the shares, or where the applicable rules specify it, a close-out is applied instead: the obligation is settled in cash at a reference price set by the shortage rules, conventionally derived from the higher of a defined benchmark and a percentage uplift over the settlement or highest traded price across a specified period.

The economics are deliberately punitive, because the framework's purpose is deterrence rather than compensation. A short seller who fails to deliver can face a close-out price substantially above the market, and the loss is uncapped in the sense that it depends on where the reference price lands.

Preventing failure is entirely within a trader's control and consists of the disciplines in the preceding section: knowing the delivery obligation in rupees and shares before expiry week, closing or rolling positions the trader cannot settle, and ensuring shares are free of pledge in time.

Auction procedures, close-out formulas, penalty rates and reference-price definitions are exchange and clearing corporation rules revised periodically; verify against the current exchange/SEBI circular before relying on this. Nothing in this document is legal, investment or operational advice for any specific situation; it describes settlement mechanics only.
