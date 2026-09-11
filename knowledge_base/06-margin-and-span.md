---
doc_id: KB-06
title: Margin and SPAN
category: risk
last_reviewed: 2026-08-15
authority: educational
---

# Margin and SPAN

## Why Margin Exists in Derivatives

Margin in the equity derivatives market is collateral deposited with the clearing corporation to cover the loss a position could plausibly incur before that loss can be collected in cash. It exists because a derivative creates an obligation without an upfront exchange of full value: a futures contract with a notional value of 15 lakh rupees changes hands with no payment at all, so the clearing corporation must hold something against the possibility that the losing side cannot pay.

The clearing corporation stands as central counterparty to every trade after novation, guaranteeing settlement to both sides. That guarantee is only as good as the resources behind it, and margin is the first and largest of those resources. Behind it sit the clearing member's own capital, the settlement guarantee fund and a defined default waterfall.

Margin is calibrated to a specific question: how much could this portfolio lose over the period between the last collection of losses and the next opportunity to close it out? In Indian equity derivatives, positions are marked to market daily, so initial margin is sized to cover roughly a one-day adverse move at a high confidence level, with additional layers added for tail risk, concentration and specific product features.

Margin is not a cost in the sense that premium is; it is returned when the position closes, subject to profit and loss. But it has an opportunity cost, it can be called at short notice, and shortfalls attract penalties. Margin frameworks, percentages and methodologies are set by SEBI and the clearing corporations and are revised periodically; verify against the current exchange/SEBI circular before relying on this.

## The SPAN Methodology

SPAN — Standardised Portfolio Analysis of Risk — is the portfolio-based margin methodology used by Indian clearing corporations to compute initial margin on derivatives positions. Rather than summing a fixed margin for each contract, SPAN evaluates the whole portfolio under a set of hypothetical market scenarios and charges margin equal to the worst outcome it finds.

The core mechanism is the risk array. For each contract, the clearing corporation defines a set of scenarios — typically sixteen — combining specified moves in the underlying price with specified moves in volatility, at fractions and multiples of a defined price scan range and volatility scan range. Each scenario produces a hypothetical profit or loss for each position. Positions are grouped by underlying, offsets are applied within a group, and the scenario producing the largest aggregate loss determines the scan risk for that group.

To scan risk, SPAN adds several further components. An intra-commodity or calendar spread charge accounts for the fact that different expiries of the same underlying do not move perfectly together, so a calendar spread is not riskless. A short option minimum charge sets a floor on the margin for deep out-of-the-money short options, whose scenario loss might otherwise appear trivially small. A delivery or spot-month charge applies where physical settlement risk arises. Inter-commodity credit may reduce margin where two underlyings are correlated, though Indian practice applies this conservatively.

The result is that SPAN margin for a hedged portfolio can be dramatically lower than for the sum of its legs traded outright, and that adding a hedging leg to an existing position can reduce total margin rather than increase it.

## Initial Margin, Exposure Margin and Total Margin

Total margin on an Indian equity derivatives position is conventionally the sum of SPAN margin and exposure margin, and understanding the split matters because they answer different questions. SPAN margin, described above, is the portfolio scenario-based component covering a plausible one-day adverse move. Exposure margin, sometimes called extreme loss margin, is an additional flat-rate layer charged on top to cover moves beyond the scenario range and to cover residual risks that scenario analysis does not capture.

Exposure margin is typically expressed as a percentage of the notional value of the position for futures and short options, with illustrative levels in the region of three percent of notional for index futures and higher for single-stock positions, subject to a floor related to the underlying's volatility. Index option positions attract exposure margin on the notional of short legs. These percentages are set by the clearing corporation and revised; verify against the current exchange/SEBI circular before relying on this.

An illustration for one lot of NIFTY futures at 24,000 with lot size 75, giving notional value of 18,00,000 rupees: if SPAN were approximately 9 percent of notional and exposure margin 3 percent, total margin would be about 12 percent, or roughly 2,16,000 rupees. For BANKNIFTY at 52,000 with lot size 30, notional is 15,60,000, and a higher combined rate reflecting greater volatility might give roughly 2 lakh rupees or more.

Brokers frequently require margin above the exchange minimum, applying their own risk buffers, higher requirements for expiry-week single-stock positions and product-specific limits. The exchange requirement is a floor, not a ceiling.

## Premium Margin and Option Buyer Requirements

Option buyers in the Indian market do not post initial margin, because their maximum loss is the premium and that premium is paid in full at trade time. The amount collected from a buyer is the premium margin: simply the premium payable, blocked at order placement and settled through the pay-in on the following business day under the applicable settlement cycle.

The asymmetry is intuitive. A buyer who has paid 11,250 rupees for one lot of a NIFTY 24,000 call at premium 150 can lose at most that 11,250, and it is already in the clearing system. No adverse market move can create a further claim against the buyer, so no scenario-based margin is required. Once the premium is paid, a long option position cannot generate a margin call.

Option writers are treated entirely differently, because their loss is not bounded by the premium received. A writer posts SPAN plus exposure margin computed on the position's scenario risk, and the premium received is credited to the writer, reducing net funds required but not eliminating the margin requirement. As the short option moves in-the-money or as volatility rises, the writer's SPAN margin increases, generating a call for additional collateral even before any loss is settled in cash.

A practical consequence for combination strategies is that the buyer's premium and the writer's margin interact within one portfolio. In a bull call spread, the long leg's premium is paid and the short leg's margin is largely offset by the long leg's protection, so total funds required approximate the net debit plus a small buffer. Actual treatment depends on the clearing corporation's current spread recognition rules; verify against the current exchange/SEBI circular before relying on this.

## Mark-to-Market Margin and Daily Cash Flows

Mark-to-market margin is the daily settlement of unrealised profit and loss on futures positions, and it is distinct from initial margin in both purpose and behaviour. Initial margin is collateral held against future risk; mark-to-market is the actual cash transfer of losses already incurred. Because losses are collected daily, initial margin only ever needs to cover one day of exposure.

The mechanics run on a daily cycle. At the end of each session the clearing corporation computes a daily settlement price for each futures contract, revalues every open position against it, and generates a debit or credit. Debits must be funded by the pay-in deadline on the following business day; credits are released as pay-out. A position opened during the day is marked from its trade price; a position carried forward is marked from the previous settlement price.

Option positions are treated differently. Long and short option positions are generally not subject to mark-to-market in the same daily-cash sense as futures; instead, changes in option value flow through the margin computation, with short option positions seeing their SPAN requirement move as the position's risk changes. On expiry, final settlement replaces mark-to-market.

The cash-flow implication is the one that catches traders. A position that will be profitable at expiry can still require substantial cash along the way if it moves adversely first. A short futures position that rises 5 percent before falling back must fund the interim loss in cash, and inability to fund it forces closure at the worst point. Funding capacity is therefore a distinct constraint from margin capacity.

## Peak Margin and Intraday Margin Reporting

Peak margin refers to the framework under which brokers must ensure clients have sufficient margin not merely at end of day but at points sampled during the trading session. The clearing corporation takes multiple snapshots of client positions through the day, computes the margin requirement at each, and the highest of those — the peak — becomes the benchmark against which the client's available collateral is judged.

The purpose is to close a gap that existed under end-of-day-only reporting: a client could take a large intraday position with little collateral, square it before the close, and never appear undermargined in any report, even though the clearing system carried real risk for hours. Peak margin reporting makes intraday exposure visible and enforceable.

The practical effect on trading is significant. Intraday leverage offered by brokers is constrained, because a broker cannot fund a client's intraday position from its own resources without the client's collateral being in place at the snapshot times. Strategies that relied on very high intraday leverage, including some day-trading approaches in single-stock futures, became materially more capital-intensive as this framework was phased in.

Reporting also drives penalties. Where a client's collateral falls short of the peak requirement, a short-collection or shortfall penalty is levied, typically as a percentage of the shortfall amount, escalating with the frequency and duration of shortfalls. Illustrative penalty rates start at a low single-digit percentage of the shortfall and increase for repeated occurrences; verify against the current exchange/SEBI circular before relying on this.

## Collateral, Pledging and Haircuts

Margin obligations in the Indian derivatives market can be met with cash or with approved non-cash collateral, and the rules around pledging shape how capital-efficient a derivatives book can be. Cash is accepted at full value. Approved securities — including listed equities on an eligible list, exchange-traded funds, mutual fund units, government securities and fixed deposits with approved banks — are accepted after a haircut, which is a percentage reduction reflecting the collateral's own price risk and liquidity.

Illustratively, a liquid large-cap equity might carry a haircut in the region of 20 percent, meaning shares worth 10 lakh rupees provide about 8 lakh of collateral value, while a government security or liquid fund unit carries a much smaller haircut. Haircut schedules and the eligible collateral list are set by the clearing corporation and revised regularly; verify against the current exchange/SEBI circular before relying on this.

A separate and important constraint is the cash-equivalent requirement. Clearing corporations require that a minimum proportion of total margin — commonly described as fifty percent — be met with cash or cash-equivalent collateral, with the balance permitted in other securities. A trader whose entire collateral is pledged equity therefore cannot use it all, and must maintain cash or cash equivalents alongside.

Pledging itself operates through a margin pledge mechanism in which securities remain in the client's demat account and a pledge is created in favour of the broker and clearing corporation, with the client authorising it through a depository-level confirmation. This replaced earlier arrangements in which securities moved to broker accounts. Mark-to-market losses on derivatives generally must be settled in cash and cannot be met by pledging more securities.

## Margin Shortfall and the Penalty Framework

A margin shortfall arises when the collateral available to support a client's derivatives positions is less than the margin those positions require, and the Indian framework treats it as a reportable, penalised event rather than a negotiable overdraft. Shortfalls are identified against end-of-day requirements and against the peak intraday requirement described earlier.

Penalties are structured to escalate. An illustrative structure charges a low single-digit percentage of the shortfall amount for smaller or occasional shortfalls, a higher percentage for larger shortfalls, and further escalation where shortfalls recur on multiple days within a month or persist beyond a threshold number of consecutive days. Penalty rates, thresholds and escalation triggers are set by the exchanges and SEBI and are revised; verify against the current exchange/SEBI circular before relying on this.

Penalties are levied on the clearing member, who passes them to the trading member and ultimately to the client whose position caused them. Beyond the monetary charge, persistent shortfalls can attract disabling of the client's trading facility and regulatory attention on the member.

Operationally, shortfalls arise in predictable ways: a mark-to-market loss debited overnight without funds available, a volatility spike expanding SPAN requirements on short option positions, a haircut increase reducing pledged collateral value, an expiry-week margin escalation on single-stock positions, or a corporate action changing collateral eligibility. Because several of these can occur without any action by the trader, maintaining a margin buffer above the computed requirement is standard practice. The controls that prevent shortfalls are covered in the operational-controls document.

## Margin Benefit for Hedged and Spread Positions

Margin benefit is the reduction in total margin that arises when positions within a portfolio offset each other's risk, and because Indian clearing uses SPAN's portfolio approach the benefit can be very large. The mechanism is straightforward: SPAN charges the worst aggregate scenario loss for a group of positions on the same underlying, so a position that loses in the scenario where another gains reduces the group's worst case.

Concrete illustration. One lot of short NIFTY 24,200 calls attracts full SPAN plus exposure margin on a position with unlimited theoretical loss. Adding a long 24,400 call caps the loss at 200 points per unit, so the worst scenario loss falls dramatically, and total margin for the resulting bull call spread can be a small fraction of the naked short's requirement. The same logic makes an iron condor far cheaper in margin than a short strangle of identical short strikes.

Calendar spreads receive partial benefit. Because different expiries of the same underlying are highly but not perfectly correlated, SPAN applies a calendar spread charge rather than granting a full offset, and the charge typically increases as the near leg approaches expiry, since the two contracts decouple.

Futures-versus-option hedges also earn benefit: a short call delta-hedged with long futures presents a smaller worst-case scenario than either leg alone. Cross-underlying offsets — index futures against a basket of single-stock positions, for example — are recognised only to the extent the clearing corporation permits inter-commodity credits, and Indian practice is conservative here.

Two cautions. Margin benefit is withdrawn when a hedging leg is removed, so closing the long wing of a spread converts it instantly into a naked short with a large margin call. And expiry-day treatment can differ. Verify current spread and hedge recognition rules against the exchange contract specification master and current circulars before relying on this.

## Physical Delivery Margins in Single-Stock F&O

Physical delivery margins are the escalated margin requirements applied to single-stock futures and options positions as expiry approaches, and they exist because physical settlement transforms a leveraged derivative into a full-value share transaction. In India, index derivatives are cash-settled while single-stock F&O is physically settled at expiry, so this escalation applies only to the stock segment.

The mechanism is a staged increase over the final sessions of the expiry week. Positions likely to result in delivery — in-the-money options and all open futures — attract progressively higher margins, moving from normal derivative margin toward the full value margin applicable to a delivery obligation. An illustrative pattern applies a fraction of delivery margin four sessions before expiry, increasing each session until close to full delivery margin on expiry day. The staging schedule and the fractions applied are set by the clearing corporation and revised; verify against the current exchange/SEBI circular before relying on this.

The magnitudes involved are large. One lot of ITC futures at lot size 1600 and an illustrative price of 450 represents a delivery obligation of 7,20,000 rupees; one lot of SBIN at 750 shares and 800 rupees is 6,00,000. A trader holding several such lots into expiry week can see margin requirements multiply within days.

Brokers commonly go further, requiring full delivery margin earlier than the exchange schedule and squaring off client positions ahead of an internal cut-off if the client has not demonstrated capacity to deliver or take delivery. Traders who intend to close rather than deliver should therefore act well before the final session, a point developed in the operational-controls document.

## Cross-Margining and Portfolio-Level Efficiency

Cross-margining is the recognition of offsetting risk across market segments — most importantly between a cash equity position and an opposite derivatives position on the same underlying — so that margin is charged on the net rather than the gross exposure. It exists because a trader who is long shares and short the corresponding future has very little market risk, and charging full margin on both legs would overstate the clearing corporation's exposure.

The classic application is the cash-and-carry arbitrage described in the futures document. An arbitrageur long 500 shares of RELIANCE in the cash segment and short one lot of RELIANCE futures has an economically flat position, and under a cross-margining arrangement the combined margin requirement is far below the sum of independent requirements. This is what makes basis arbitrage viable at all, since the gross basis captured is small relative to full margin on both legs.

Eligibility conditions apply. Cross-margining typically requires the positions to be in the same underlying, held in accounts recognised as belonging to the same entity, and reported through the prescribed process to the clearing corporation. Index-futures-against-basket arrangements have existed for institutional participants with defined basket-replication requirements.

Portfolio-level efficiency more broadly comes from three sources: SPAN's scenario netting within an underlying, spread and hedge recognition across expiries and strikes, and cross-segment recognition where permitted. A trader designing a book for capital efficiency is effectively designing for low worst-case scenario loss.

Cross-margining eligibility, procedures and benefit levels are set by SEBI and the clearing corporations and change over time; verify against the current exchange/SEBI circular before relying on this. Nothing in this document is investment or legal advice; it describes margin mechanics only.
