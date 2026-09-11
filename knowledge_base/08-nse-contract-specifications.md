---
doc_id: KB-08
title: NSE Contract Specifications
category: reference
last_reviewed: 2026-08-15
authority: educational
---

# NSE Contract Specifications

## What a Contract Specification Contains

A contract specification is the exchange's definition of a derivative contract, and it is the authoritative source for every parameter a trading or risk system needs. It is published in the exchange contract specification master and updated as parameters change, which they do regularly. A specification contains the underlying, the instrument type, the market lot or lot size, the tick size, the strike interval and number of strikes for options, the expiry convention, the last trading day, the daily settlement price methodology, the final settlement price methodology, the settlement type (cash or physical), the price operating range, the quantity freeze limit and the position limit basis.

Every number in this document is illustrative and reproduced for teaching purposes only. Lot sizes are revised when the exchange rebalances contract value against regulatory guidance on minimum contract size. Strike intervals widen and narrow. Freeze quantities change with liquidity. Expiry weekday assignments have been reorganised more than once. Verify against the current exchange/SEBI circular and the exchange contract specification master before relying on this.

The practical rule for system design is that no contract parameter should be hard-coded. Lot size, tick size, expiry date, settlement type and freeze quantity should all be read from the exchange's daily contract master file and refreshed each session. A system that assumes a NIFTY lot of 75 will silently mis-size every position after a lot revision, and a system that assumes a Thursday expiry will mis-handle holiday-shifted expiries and any future reorganisation of weekly expiry days.

## Index Futures Specifications

Index futures on the Indian exchanges cover the four benchmarks in this project's scope, and their parameters differ enough that position sizing must be contract-specific. NIFTY futures use a lot size of 75, BANKNIFTY 30, FINNIFTY 65 and MIDCPNIFTY 120. All four are cash-settled at expiry against the index's final settlement value, computed from a volume-weighted average over a defined closing window on expiry day rather than a single print.

Tick size for index futures is conventionally five paise, meaning quoted prices move in increments of 0.05 index points. Contracts are listed for three serial monthly expiries — near, next and far — with a new far month introduced as the near month expires. Monthly expiry is the last Thursday of the expiry month, moving to the preceding business day when that Thursday is a trading holiday.

Notional value per lot follows from price times lot size. Illustratively: NIFTY at 24,000 gives 18,00,000 rupees per lot; BANKNIFTY at 52,000 gives 15,60,000; FINNIFTY at 23,500 gives 15,27,500; MIDCPNIFTY at 12,800 gives 15,36,000. The rough parity of notional values across contracts is deliberate — lot sizes are set so that contract value sits within a target band.

Daily settlement price is derived from the volume-weighted average price of trades in the closing window, with a theoretical price used where no trading occurs. Price operating ranges apply and can be widened by the exchange when genuine interest exists beyond them. All values illustrative; verify against the current exchange/SEBI circular before relying on this.

## Index Options Specifications

Index options are the highest-volume contracts in the Indian derivatives market, and their specifications combine weekly and monthly expiries with dense strike ladders. Lot sizes match the corresponding futures: NIFTY 75, BANKNIFTY 30, FINNIFTY 65, MIDCPNIFTY 120. All index options are European-style and cash-settled, with in-the-money contracts automatically exercised at expiry against the index's final settlement value.

Weekly expiry days used by this project are NIFTY Thursday, BANKNIFTY Wednesday, FINNIFTY Tuesday and MIDCPNIFTY Monday, with monthly expiry on the last Thursday. The number of weekly expiries listed at any time, and which indices carry them, are exchange product decisions that have been revised, including consolidation onto fewer underlyings; verify against the current exchange/SEBI circular before relying on this.

Strike intervals are illustratively 50 points for NIFTY near the money, 100 for BANKNIFTY, 50 for FINNIFTY and 25 for MIDCPNIFTY, with intervals widening for strikes further from spot. The exchange lists strikes spanning a defined percentage band around the prevailing index level and introduces additional strikes as the index moves, so the ladder extends automatically.

Tick size is five paise on the premium. Premium quotations are per unit of index, so a NIFTY call quoted at 150 costs 150 × 75 = 11,250 rupees per lot. Because premium and index are quoted in the same units, a common error is to compute profit against index points without applying the lot size.

## Single-Stock Futures Specifications

Single-stock futures are listed only on shares in the exchange's F&O-eligible list, and their defining feature is physical settlement at expiry. Lot sizes used consistently across this knowledge base are illustrative: RELIANCE 500, TCS 175, INFY 400, HDFCBANK 550, ICICIBANK 700, SBIN 750, ITC 1600, AXISBANK 625. Lot sizes are set so that contract value falls within a target band, which is why a high-priced share like TCS carries a small lot and a low-priced share like ITC carries a large one.

Illustrative notional values per lot: RELIANCE at 2,900 gives 14,50,000 rupees; TCS at 3,900 gives 6,82,500; INFY at 1,600 gives 6,40,000; HDFCBANK at 1,650 gives 9,07,500; ICICIBANK at 1,250 gives 8,75,000; SBIN at 800 gives 6,00,000; ITC at 450 gives 7,20,000; AXISBANK at 1,150 gives 7,18,750. Each of these becomes a delivery obligation if the position is carried through expiry.

Single-stock futures are listed for three serial monthly expiries with monthly expiry on the last Thursday. There are no weekly single-stock contracts. Tick size is five paise. Final settlement price is derived from the underlying share's closing price in the cash segment on expiry day, computed under the cash market's weighted-average closing methodology.

Stocks enter and exit the F&O-eligible list as liquidity and market-capitalisation criteria under SEBI circulars on the F&O framework are applied periodically. When a stock exits, existing contracts are typically allowed to run off with no new series introduced. Verify current eligibility, lot sizes and expiry dates against the exchange contract specification master before relying on this.

## Single-Stock Options Specifications

Single-stock options in India are listed on monthly expiries only, are European-style, and are physically settled at expiry — a combination that makes them operationally heavier than index options despite being conceptually identical. Lot sizes match the corresponding stock futures: RELIANCE 500, TCS 175, INFY 400, HDFCBANK 550, ICICIBANK 700, SBIN 750, ITC 1600, AXISBANK 625, all illustrative.

Strike intervals vary with the share's price level, following a schedule that assigns smaller intervals to lower-priced shares. Illustratively, a share trading near 450 like ITC might carry strikes at 5 or 10-rupee intervals, one near 1,600 like INFY at 20 or 25-rupee intervals, and one near 3,900 like TCS at 50 or 100-rupee intervals. The exchange lists strikes spanning a percentage band around the current price and adds strikes as the share moves.

Physical settlement means an in-the-money option carried to expiry produces a share transaction at the strike. One lot of an in-the-money ITC call at strike 440 requires paying 440 × 1600 = 7,04,000 rupees to receive 1,600 shares. An assigned short SBIN put at strike 780 requires paying 780 × 750 = 5,85,000 rupees.

Delivery margins escalate on a staged schedule through the final sessions of expiry week for positions likely to result in delivery, and brokers commonly apply stricter requirements earlier. Tick size on the premium is five paise. Strike interval schedules, delivery margin staging and eligibility are exchange parameters revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Lot Size Determination and Revisions

Lot size determination in Indian equity derivatives follows from a target contract value rather than from any property of the share itself, which explains the wide dispersion in lot sizes across underlyings. SEBI has periodically prescribed a minimum contract value for derivatives, and exchanges set lot sizes so that a contract's notional value sits at or above that minimum while remaining within a practical band. When a minimum contract value is raised, lot sizes across the market are revised upward.

The arithmetic is direct. If the target contract value is roughly 15 lakh rupees and NIFTY trades near 24,000, a lot of 75 gives 18,00,000 — comfortably above the floor with room for the index to fall. If ITC trades near 450, a lot of 1600 gives 7,20,000. The dispersion between 75 and 1600 is entirely a function of price level.

Revisions happen for two reasons: a change in the prescribed minimum contract value, and drift in the underlying's price far enough that the existing lot size produces a contract value outside the intended band. Exchanges announce revisions in advance and apply them to newly introduced contracts, with existing open positions adjusted so that economic exposure is preserved rather than changed.

The system-design implication is that lot size is a time-varying, contract-level attribute. Position-sizing code, margin estimation, profit-and-loss computation and risk limits all depend on it, and all should read it from the exchange contract specification master each session. All lot sizes in this knowledge base are illustrative teaching values; verify against the current exchange/SEBI circular before relying on this.

## Tick Size, Price Bands and Operating Ranges

Tick size is the minimum permissible price increment for a contract, and in Indian equity derivatives it is conventionally five paise for both futures and option premiums. An order priced at a non-multiple of the tick is rejected. Tick size sets a floor on the bid-ask spread and therefore on the round-trip cost of trading: a one-tick spread on a NIFTY option is 0.05 × 75 = 3.75 rupees per lot, negligible on a premium of 150 but a large percentage of a premium of 0.50.

Price operating ranges constrain where orders may be priced. Rather than a hard daily circuit of the kind applied to individual cash-market shares, derivatives contracts operate within a dynamic range around a reference price, and orders outside the range are rejected at entry. Where genuine trading interest exists beyond the range, the exchange can widen it through a defined process, typically after a short cooling period. Illustrative ranges are expressed as a percentage of the reference price and differ between futures and options and between near and far strikes.

The interaction that surprises traders is that a fast-moving market can leave a contract's operating range behind, so that limit orders at the price the trader believes is current are rejected. This is a common cause of failed exits during sharp moves, and it is a reason to monitor rejection messages rather than assume an order rested in the book.

In the cash segment, individual securities carry circuit filters and index-level circuit breakers can halt the whole market at defined percentage moves. A market-wide halt suspends derivatives trading too. Range percentages, filter levels and halt rules are exchange parameters revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Quantity Freeze and Order Size Limits

Quantity freeze is the maximum quantity permitted in a single order for a given contract, and exceeding it does not simply reject the order — it flags the order for exchange confirmation, introducing delay and uncertainty. The purpose is to catch erroneous large orders before they hit the book, which makes the freeze limit an exchange-level fat-finger control.

Freeze quantities are set per contract and expressed in units of the underlying rather than in lots, so the equivalent number of lots differs across contracts. Illustratively, if a NIFTY contract's freeze quantity were 1,800 units, that is 24 lots at a lot size of 75; a BANKNIFTY freeze of 900 units is 30 lots at a lot size of 30. Freeze quantities are revised periodically in line with liquidity, and index and single-stock contracts carry different levels.

The operational consequence is that large positions must be built and unwound through multiple orders below the freeze threshold. A trader attempting to exit 100 lots in one order in a falling market may find the order held for confirmation rather than executed, which is precisely the wrong outcome under stress. Execution systems should therefore slice orders automatically against the current freeze quantity read from the contract master.

Brokers layer their own limits on top: maximum order value, maximum order quantity, maximum open position per client and per contract, and product-specific restrictions during expiry week. These broker limits are usually tighter than exchange limits and can be changed without notice. Freeze quantities and broker limits are both revised regularly; verify against the current exchange/SEBI circular and your broker's policy before relying on this.

## Strike Intervals and Strike Ladder Construction

Strike intervals determine how finely the option chain is divided, and the exchange constructs the ladder dynamically so that strikes are always available around the prevailing price. The general principle is a narrow interval near the money and wider intervals further away, with additional strikes introduced automatically as the underlying moves toward the edge of the existing ladder.

Illustrative index intervals: NIFTY at 50 points near the money, BANKNIFTY at 100, FINNIFTY at 50, MIDCPNIFTY at 25, each widening at distance. For single stocks, intervals follow a price-band schedule — smaller absolute intervals for lower-priced shares — so ITC near 450 carries much tighter strike spacing in rupees than TCS near 3,900, while the percentage spacing is broadly comparable.

The exchange lists strikes covering a defined percentage band around the current level, and the band is wider for longer-dated contracts than for weekly ones, because the underlying has more scope to move. As the index moves, new strikes at the edge appear and become tradeable, initially with no open interest and typically wide spreads.

Two consequences matter for systems. First, the strike ladder is not static, so a chain snapshot taken at the open may lack strikes that exist by midday. Second, liquidity is a function of distance from spot rather than of the strike's existence: a listed strike far from spot may have no bid, no ask, or a spread wide enough to make it untradeable in practice. Strike interval schedules and band widths are exchange parameters revised periodically; verify against the current exchange/SEBI circular before relying on this.

## Contract Symbols, Instrument Types and Identifiers

Contract identification in the Indian derivatives market follows a structured symbology, and getting it wrong is one of the most common causes of erroneous orders. A contract is identified by the combination of instrument type, underlying symbol, expiry date and — for options — strike price and option type.

Instrument types distinguish the product families: index futures, stock futures, index options and stock options are separate categories in the exchange contract master, and a system must not treat a symbol as unique without its instrument type. Option type is CE for a call and PE for a put, following the European-style convention.

A typical option symbol composes underlying, expiry, strike and option type — for example a NIFTY call at strike 24500 expiring on a given date reads in the form NIFTY<expiry>24500CE, and the corresponding put NIFTY<expiry>24500PE. A futures contract omits strike and option type, commonly written as NIFTY<expiry>FUT. Exchange feeds also carry a numeric instrument token that is the reliable primary key, since text symbols can be reformatted between systems.

Two failure modes recur. Confusing CE and PE places a directionally opposite trade, and because premiums for equidistant calls and puts are often similar, the error is not obvious from the order value. Selecting the wrong expiry from a chain that lists several weeklies plus monthlies produces a position with unintended time exposure and, for single stocks, unintended delivery timing.

The control is to trade from the exchange instrument token rather than a reconstructed string, and to display underlying, expiry, strike and option type explicitly on every confirmation. Symbol formats and token schemes are exchange conventions revised periodically; verify against the exchange contract specification master before relying on this.

## Using the Contract Master in Automated Systems

The exchange contract specification master is the daily file that lists every tradeable contract with its full parameter set, and consuming it correctly is the foundation of a reliable automated derivatives system. It provides the instrument token, symbol, instrument type, underlying, expiry date, strike, option type, lot size, tick size, freeze quantity and, in accompanying files, price bands and settlement parameters.

Sound practice has a few rules. Download and reload the master at the start of every trading session, because contracts are added and removed daily as weeklies expire and new series list. Key all internal records on the instrument token, not on a constructed symbol string. Read lot size and tick size from the master at order-construction time rather than from a configuration file. Read the expiry date from the master rather than computing it from a weekday rule, so that holiday shifts and product reorganisations are handled automatically. Read settlement type from the master so that physical-settlement handling is applied to single-stock contracts without a hard-coded list.

Validation checks are worth building in. Reject any order whose quantity is not a whole multiple of the current lot size, whose price is not a multiple of the tick, or whose quantity exceeds the current freeze quantity without explicit slicing. Flag any position whose contract will expire within a configured number of sessions, and separately flag physically settled positions with their computed delivery value in rupees.

Every parameter in this document is an illustrative teaching value, and all of them change. Verify against the current exchange/SEBI circular and the exchange contract specification master before relying on this. Nothing in this document is investment advice; it describes contract parameters only.
