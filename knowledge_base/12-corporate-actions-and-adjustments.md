---
doc_id: KB-12
title: Corporate Actions and Adjustments
category: operations
last_reviewed: 2026-08-15
authority: educational
---

# Corporate Actions and Adjustments

## Why Derivatives Need Adjustment for Corporate Actions

Corporate actions change the number of shares outstanding, the value attached to each share, or both, and derivative contracts written on those shares must be adjusted so that the economic position of holders is preserved rather than altered by an event they did not choose. Without adjustment, a two-for-one stock split would halve the underlying's price overnight and convert every in-the-money call into a worthless one, purely as an accounting artefact.

The governing principle is value neutrality: after adjustment, the holder of a derivative position should hold approximately the same economic exposure and the same value as immediately before, ignoring market movement. The exchange achieves this by adjusting one or more of three contract terms — the strike price, the market lot or position size, and in some cases the contract price itself — using an adjustment factor derived from the action.

Adjustments are applied by the exchange with effect from the ex-date, the first date on which the share trades without entitlement to the action. Positions are adjusted automatically; no action is required from holders, though holders must understand what their position has become.

Not every corporate action triggers an adjustment. Ordinary dividends within a normal range are conventionally left unadjusted, because their effect is already anticipated in futures and option pricing through the dividend term in cost of carry. Extraordinary dividends above a defined threshold are adjusted. The specific rules, thresholds and formulas are exchange rules revised periodically; verify against the current exchange/SEBI circular and the exchange contract specification master before relying on this.

## The Adjustment Factor and General Methodology

The adjustment factor is the single number that expresses how a corporate action changes the value of one share, and every derivative adjustment flows from it. Conceptually, the factor is the ratio of the share's value immediately before the action to its theoretical value immediately after, computed on a per-share basis.

The general methodology applies the factor in a consistent direction. Strike prices are divided by the factor where the factor is expressed as the ratio of new shares to old, so a split that doubles the share count halves every strike. Market lot and position size are multiplied by the same ratio, so a holder of one lot of 500 shares holds one lot of 1,000 after a two-for-one split. Futures contract prices are adjusted correspondingly, with the difference between the pre-adjustment and post-adjustment price settled through the mark-to-market mechanism so that no value is created or destroyed.

The arithmetic check is that strike multiplied by lot size — the rupee value of exercising one contract — remains approximately constant, as does contract price multiplied by lot size. If a RELIANCE call at strike 3,000 with lot size 500 represents 15,00,000 rupees of exercise value, then after a two-for-one split the strike of 1,500 with lot size 1,000 represents the same 15,00,000.

Rounding introduces small residuals, since adjusted strikes must land on permissible price increments and lot sizes must be whole numbers. Exchanges specify rounding conventions to keep residuals immaterial. Where an action cannot be adjusted cleanly — certain schemes of arrangement, for instance — the exchange may instead close out contracts at a determined value. All methodology described here is a general educational summary; the operative formulas are the exchange's.

## Stock Splits and Their Effect on F&O Contracts

A stock split divides each existing share into a larger number of shares of smaller face value, leaving total company value unchanged, and the derivative adjustment is the cleanest of all corporate action adjustments because the factor is exact.

The mechanics for a two-for-one split, using RELIANCE with an illustrative lot size of 500 and a pre-split price of 2,900: on the ex-date the share trades at approximately 1,450. Every strike is halved, so the 3,000 call becomes a 1,500 call and the 2,800 put becomes a 1,400 put. The market lot doubles from 500 to 1,000. A holder of one lot of the 3,000 call before the split holds one lot of the 1,500 call after it, and the exercise value of 3,000 × 500 = 15,00,000 becomes 1,500 × 1,000 = 15,00,000, unchanged.

Futures adjust the same way. A long position at a futures price of 2,920 with lot size 500 becomes a long position at 1,460 with lot size 1,000, and the notional value of 14,60,000 is preserved.

A five-for-one split multiplies lot size by five and divides strikes by five. Where the resulting strike is not a permissible increment, the exchange's rounding convention applies.

The practical consequences are two. First, the number of shares in a delivery obligation changes, so a physically settled single-stock position carries a different share count after the split — relevant for expiry planning. Second, any system that stores lot size or strike locally must refresh from the exchange contract specification master on the ex-date, or every downstream calculation will be wrong.

## Bonus Issues

A bonus issue distributes additional shares to existing holders without payment, capitalising reserves, and its effect on derivative contracts is arithmetically identical to a stock split even though the corporate mechanics differ. A one-for-one bonus gives each holder one additional share per share held, doubling the share count and approximately halving the price.

Using INFY with an illustrative lot size of 400 and a pre-bonus price of 1,600: a one-for-one bonus results in an ex-date price near 800. Strikes are halved, so the 1,700 call becomes an 850 call. Lot size doubles from 400 to 800. Exercise value is preserved: 1,700 × 400 = 6,80,000 becomes 850 × 800 = 6,80,000.

For a bonus in a ratio other than one-for-one, the factor is computed from the resulting total share count. A one-for-two bonus — one new share for every two held — increases the share count by fifty percent, so the adjustment ratio is three to two: strikes are multiplied by two-thirds and lot size by three-halves. Applied to ITC with an illustrative lot size of 1600, the new lot would be 2,400, and a strike of 450 would become 300.

The adjustment takes effect from the ex-bonus date. Because bonus adjustments frequently produce lot sizes that differ substantially from the exchange's preferred contract value band, the exchange may subsequently revise the lot size in a separate action once the adjusted contracts expire.

Traders should note that the number of contracts held does not change — one lot remains one lot — but what a lot represents does. Verify adjusted parameters against the exchange contract specification master on the ex-date before relying on this.

## Dividends: Ordinary and Extraordinary

Dividends occupy a distinctive place in derivative adjustment because most of them are not adjusted at all. The reason is that expected dividends are already embedded in derivative prices through the cost-of-carry relationship: a futures price is spot times the carry factor less the present value of dividends expected before expiry, so an anticipated dividend is priced in well before the ex-date.

The convention is therefore that ordinary dividends produce no adjustment to strikes or lot sizes. When the share goes ex-dividend and its price falls by approximately the dividend amount, derivative holders experience that fall without compensation, because they were never entitled to the dividend and the futures price had already reflected its expected payment.

Extraordinary dividends are treated differently. Where a dividend exceeds a defined threshold — conventionally expressed as a percentage of the share's market price, with an illustrative threshold in the region of two percent — the exchange treats it as extraordinary and adjusts contracts. The adjustment typically reduces strike prices by the dividend amount per share, leaving lot size unchanged, so that the derivative holder is not disadvantaged by an unusually large distribution.

Illustratively, if HDFCBANK at 1,650 declared a dividend of 60 rupees per share, that is above the illustrative threshold, and strikes would be reduced by 60: a 1,700 call becomes a 1,640 call, with the lot size of 550 unchanged.

Thresholds, the treatment of special versus interim dividends, and the exact adjustment formula are exchange rules revised periodically; verify against the current exchange/SEBI circular before relying on this. This section describes adjustment mechanics only and offers no view on dividend-related trading.

## Rights Issues

A rights issue offers existing shareholders the opportunity to buy additional shares at a price below the prevailing market price, and because the right itself has value, the share's theoretical price falls on the ex-rights date by an amount that must be reflected in derivative contracts. Unlike a split or bonus, the adjustment factor is not a simple ratio of share counts, because the new shares are paid for.

The standard approach computes a theoretical ex-rights price. If a company with shares at price P offers N new shares at subscription price S for every M shares held, the theoretical ex-rights price is (M × P + N × S) / (M + N). The adjustment factor is then the ratio of the cum-rights price to this theoretical ex-rights price, and strikes are divided by that factor while lot size is multiplied by it.

An illustration using AXISBANK with an illustrative lot size of 625 and a price of 1,150: a one-for-five rights issue at 900 rupees gives a theoretical ex-rights price of (5 × 1,150 + 1 × 900) / 6 = (5,750 + 900) / 6 = 1,108.33. The factor is 1,150 / 1,108.33 ≈ 1.0376. Strikes are divided by that factor, so a 1,200 strike becomes approximately 1,156.5, subject to rounding to a permissible increment; the lot size is multiplied by it, giving approximately 649, rounded per the exchange convention.

Rights adjustments produce non-round strikes and lot sizes, which is why rounding conventions matter more here than for splits. Any automated system must read adjusted parameters from the exchange contract specification master rather than recomputing them, since the exchange's rounding is authoritative.

## Mergers, Demergers and Schemes of Arrangement

Mergers, demergers and schemes of arrangement are the corporate actions most likely to be handled by contract termination rather than by adjustment, because the underlying's identity or composition changes in ways an adjustment factor cannot capture cleanly.

In a merger where the F&O-eligible company is absorbed into another entity, the underlying share ceases to exist on the effective date. The typical treatment is that no new contract series are introduced once the scheme is approved and dated, existing contracts continue until a determined last trading day, and open positions are settled at a value determined under the exchange's procedure for the action — often a final settlement based on the last available price or on the exchange ratio applied to the acquiring company's price.

In a demerger, the original share splits into a residual share plus shares in a newly listed entity. The exchange computes an adjustment factor from the relative values of the resulting entities, typically derived from a defined price discovery process for the demerged entity, and adjusts strikes and lot sizes on the residual company's contracts accordingly. Whether derivatives are introduced on the newly listed entity depends on its own eligibility.

Schemes of arrangement covering capital reduction, buyback through a scheme, or reorganisation of share capital are handled case by case, with the exchange issuing a specific adjustment or close-out determination.

The practical implication for traders is that positions in a company undergoing such an action can be terminated at a determined value rather than traded out at a market price of the holder's choosing, and that the determination date may not align with the holder's plans. Treatment is action-specific and determined by the exchange; verify against the current exchange/SEBI circular before relying on this.

## Buybacks, Delisting and Stock Exit from F&O

Buybacks, delisting and removal from the F&O-eligible list are three distinct events that each terminate or constrain derivative trading in a share, and traders holding positions need to distinguish them.

A share buyback through the tender route or open market route does not by itself trigger a derivative adjustment, because the buyback is an offer rather than a distribution to all holders proportionally. The share's price behaviour around a buyback reflects the offer's terms, but derivative contracts continue with unchanged terms. A buyback executed through a scheme of arrangement may be treated differently.

Delisting removes the share from the exchange entirely, so derivatives on it cannot continue. The exchange stops introducing new series once a delisting process is underway, sets a last trading day, and determines settlement of open positions under its procedure for the action.

Exit from the F&O-eligible list is different from delisting: the share continues to trade in the cash segment, but its derivatives are discontinued because it no longer meets the liquidity and market-capitalisation criteria applied under SEBI circulars on the F&O framework. The standard treatment is that no new contract series are introduced, and existing series run off to their natural expiry. Traders holding positions in the longer-dated series can trade them out, but liquidity in an exiting stock's contracts typically deteriorates.

In all three cases, the practical risks are the same: reduced liquidity, a hard end date for the contract's life, and settlement at a determined rather than a chosen price. Verify the current eligible list and any specific action's treatment against the exchange contract specification master before relying on this.

## Ex-Dates, Record Dates and Contract Master Updates

Ex-date and record date are the two calendar anchors of every corporate action, and confusing them is a routine source of operational error. The record date is the date on which the company determines which shareholders are entitled to the action, from its register of members. The ex-date is the first trading date on which the share trades without the entitlement, and under a shortened settlement cycle the ex-date and record date can fall very close together.

Derivative adjustments take effect from the ex-date, not the record date, because that is when the share's price reflects the loss of entitlement. On the ex-date morning, adjusted strikes, adjusted lot sizes and adjusted futures prices are already live in the exchange contract specification master.

This produces a hard operational requirement for any automated system. The contract master must be reloaded at the start of every session, and positions must be reconciled against it. A system holding a locally cached lot size of 500 for RELIANCE after a two-for-one split will compute every profit and loss figure, every margin estimate and every delivery obligation at half its true value. A system holding a cached strike will mis-identify moneyness.

Reconciliation should check, at minimum, that each held position's contract still exists in the master, that its lot size matches the cached value, and that its strike matches. Any mismatch should be flagged for review rather than silently accepted.

Exchanges publish forthcoming corporate actions and the resulting adjustments in advance, and prudent practice is to maintain a forward calendar of actions affecting held positions. Verify all adjusted parameters against the exchange contract specification master on and after the ex-date before relying on this.

## Corporate Actions During Expiry Week

Corporate actions falling in expiry week combine two operationally demanding events, and the interaction produces risks that neither creates alone. The core difficulty is that adjustment changes the terms of a contract that is simultaneously approaching physical settlement in the single-stock segment.

Several specific hazards recur. A lot size adjustment changes the number of shares in a delivery obligation: a trader who planned to deliver 500 RELIANCE shares against one lot may find, after a split, that the obligation is 1,000 shares of the post-split share, which is economically identical but operationally different if shares were already earmarked. A strike adjustment changes moneyness relative to a mentally anchored level, so a position the trader believed was safely out-of-the-money may not be after adjustment, since the underlying's price has also changed.

An extraordinary dividend adjustment shortly before expiry reduces strikes and can move a short option from out-of-the-money to in-the-money, creating an unexpected assignment and delivery obligation. And a share going ex-dividend during expiry week experiences a price drop on the ex-date that is not a market move but is nonetheless real for delta-hedged positions.

Compounding all of this, delivery margins escalate through expiry week, and adjusted positions may attract different margin than the trader anticipated.

The control is anticipation. Maintain a calendar of corporate actions with ex-dates for every held underlying, identify overlaps with expiry weeks in advance, and decide before the ex-date whether affected positions will be closed, rolled or carried. Nothing in this document is investment advice; it describes adjustment mechanics only, and all thresholds and formulas described are illustrative and subject to the exchange's current rules.
