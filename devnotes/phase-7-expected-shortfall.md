# Phase 7: Expected Shortfall (Stage 2 begins)

_Completed 2026-11-23. Every number below comes from running `python run_es.py` on
2026-11-23 (data up to 2026-11-23)._

## Goal

VaR is a **threshold**: "we lose more than this on 1 day in 100". It says nothing
about **how much** we lose on that day. Expected Shortfall (ES) is the average loss
on the days beyond VaR. This phase adds ES to every model, compares it with VaR,
computes stressed ES, and checks whether ES was big enough on breach days.

**Why a Market Risk team cares:** Basel's newer market-risk rules (FRTB) replace
99% VaR with **97.5% ES** for capital. FRAM VaR PPT, slide 31: "Regulators have
indicated that they plan to move from using VaR to using ES."

## Concepts

### VaR vs ES (FRAM slide 31: "two portfolios with the same VaR can have very different ES")
| 3 worst of 250 days | VaR 99% (3rd worst) | ES 99% (average of the 3) |
|---|---|---|
| A: −4.0 L, −2.5 L, −1.5 L | 1.5 L | **2.67 L** |
| B: −1.6 L, −1.55 L, −1.5 L | 1.5 L | **1.55 L** |

The same VaR, but A's bad days are almost twice as bad. ES is also called CVaR or
Tail Loss.

### Historical ES
The average of every replayed day at or beyond the VaR point.
- 99%, 250 days: VaR point = 3rd worst, so ES = average of the 3 worst.
- 97.5%: position 0.025 × 249 = 6.2 → 7th worst, so ES = average of the 7 worst.

### Parametric ES
ES = σ·φ(z)/(1−α) − μ, where φ(z) is the bell curve's height at z.

| Level | z | VaR (×σ) | ES (×σ) |
|---|---|---|---|
| 99% | 2.326 | 2.326 | 2.665 |
| 97.5% | 1.960 | 1.960 | 2.338 |

So parametric ES/VaR is always 1.15 by construction, and on a bell curve ES 97.5%
≈ VaR 99%.

### Coherence (FRAM slide 22)
A "coherent" risk measure obeys four rules. The last is **subadditivity**: merging
two portfolios should never *raise* risk above the sum of their separate risks
(diversification can't hurt). VaR can break this rule (reading material, line ~1014);
ES never does.

### Small-sample noise
Historical ES 99% on 250 days averages only 3 numbers, so one crash day entering or
leaving the window moves it by a third. ML link: a 3-row test set gives a
high-variance estimate. FRTB's 97.5% uses 7 points; exponential weighting (FRAM
slides 26–30) is Phase 8.

**ML link:** VaR is the cut-off mark for the bottom 1% of a class; ES is the average
mark of the students below it.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `config.py` → `ES_CONFIDENCE = 0.975` | — | — | FRTB level, kept in config like every setting |
| `models/base.py` → `VaRModel.predict_es(window, confidence=None)` | returns window, optional level | ES in ₹ (positive) | The shared interface grows: every model must give VaR **and** ES |
| `models/base.py` → `_level(confidence)` | level or None | the level to use | None = the model's own 99% |
| `models/base.py` → `rolling_var(..., measure="var" \| "es", confidence)` | model, returns, window | Series named `historical` or `historical_es` | One rolling engine for both measures; no look-ahead, the same as Phase 2 |
| `models/historical.py` → `predict_es` | window, level | mean of the tail | `pnl[pnl <= cutoff]` (boolean indexing) uses the same `method="lower"` cutoff as VaR |
| `models/parametric.py` → `predict_es`, `_mu_sigma` | window, level | σ·φ(z)/(1−α) − μ | μ and σ moved into one helper shared by VaR and ES; VaR unchanged (verified ₹1.11 L / ₹1.09 L) |
| `backtest.py` → `es_severity(breaches, es, pnl)` | breach flags, ES forecasts, P&L | avg loss, avg ES, ratio | Simple size check: ratio 1.0 = ES right on average |
| `run_es.py` | — | prints 5 tables; writes `outputs/es_forecasts.csv` | VaR 99, ES 99, ES 97.5 for both models through history |

**Library / Python features used for the first time:**
- `scipy.stats.norm.pdf(z)`: the bell curve's height at z (`ppf` was the inverse
  of the cumulative curve).
- `series[series <= x]`: boolean indexing, keeping rows where the condition is True.
- `lambda past: ...`: a one-line unnamed function.
- A leading underscore (`_mu_sigma`): Python's convention for "internal helper".

**Hand-checks before the full run:** the Portfolio A toy gave VaR 150,000 and ES
266,667; the bell-curve multipliers came out as 2.326 / 2.665 / 2.338.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Historical ES tail | Days at or beyond the `method="lower"` VaR point (3 at 99%) | Exactly 2.5 days (weighted) | Consistent with our VaR rule; simple |
| Levels | 99% and 97.5% | 99% only | 97.5% is FRTB's level; comparing them teaches tail shape |
| ES validation | Size check on breach days (ratio) | Formal Acerbi–Székely test | Explainable first step; the formal test is a later item |
| Interface | `predict_es` on each model + `measure=` in `rolling_var` | A separate ES module | Keeps "one interface, many models"; later models (EWMA, GARCH) must provide both |

## Results (run of 2026-11-23)

**Next trading day** (window ending 23 Nov 2026), ₹ lakh:
| | VaR 99% | ES 99% | ES / VaR | ES 97.5% | ES 97.5 / VaR 99 |
|---|---|---|---|---|---|
| Historical | 1.11 | 1.41 | 1.27 | 1.17 | 1.05 |
| Parametric | 1.09 | 1.24 | 1.14 | 1.09 | 1.00 |

**Average over 4,755 days:** ES99/VaR99 = **1.23** historical vs 1.15 parametric (a
bell curve gives 1.15). ES97.5/VaR99 = 1.01 for both (a bell curve gives 1.01).
- So the worst 2–3 days are fatter than a bell curve, but around the 97.5% level the
  tail looks roughly normal. **The fat tail is concentrated in very few days.** (My
  prediction that ES97.5 vs VaR99 would show fat tails was wrong on average.)

**Stressed window** (10 Apr 2019 → 23 Mar 2020), ₹ lakh:
| | SVaR 99% | Stressed ES 99% | Stressed ES 97.5% |
|---|---|---|---|
| Historical | 3.41 | **3.77** | 2.88 |
| Parametric | 1.51 | 1.73 | 1.52 |

Historical stressed ES 97.5% is **below** SVaR 99%: the 3 worst days average 3.77 L,
the 7 worst average 2.88 L, so days 4–7 average only ~2.21 L. 97.5% ES is not
automatically more conservative than 99% VaR.

**Was ES big enough?** On VaR-breach days, average actual loss vs average ES 99%:
| | Breach days | Avg loss | Avg ES | Ratio |
|---|---|---|---|---|
| Historical | 64 | 1.53 L | 1.38 L | **1.11** (ES 11% too small) |
| Parametric | 82 | 1.42 L | 1.15 L | **1.24** (24% too small) |

23 Mar 2020: actual loss 4.19 L vs historical VaR 2.94 / ES 3.36, parametric VaR
1.36 / ES 1.56.

## Bugs and fixes

None. The refactor of parametric VaR (moving μ and σ into `_mu_sigma`) was checked
by confirming next-day VaR is unchanged (₹1.11 L / ₹1.09 L).

## Interview questions (with model answers)

1. **What's the difference between VaR and Expected Shortfall?**
   VaR is the loss threshold exceeded with 1% probability; ES is the average loss
   given that VaR is exceeded. Two portfolios can share a VaR but have very
   different ES. On my portfolio today, VaR 99% is ₹1.11 L and ES 99% is ₹1.41 L.
2. **Why did Basel move to 97.5% ES?**
   ES sees the size of tail losses, and it's coherent (subadditive), so
   diversification never increases measured risk, which VaR can't guarantee. 97.5%
   is used because on a normal distribution it roughly matches 99% VaR (2.338σ vs
   2.326σ) while using more tail points.
3. **Is 97.5% ES always more conservative than 99% VaR?**
   No. On my COVID stress window, historical ES 97.5% was ₹2.88 L vs SVaR 99% of
   ₹3.41 L: the 3 worst days were huge and days 4–7 much smaller, so averaging 7
   days dilutes them.
4. **How did you validate ES?**
   On VaR-breach days I compared the average actual loss with the average ES
   forecast. Historical ES was 11% too small, parametric 24% too small. Formal ES
   backtests like Acerbi–Székely would be the next step.
5. **What's the weakness of historical ES?**
   At 99% on 250 days it averages only 3 points, so it's very noisy and jumps when
   one crash enters or leaves the window. Fixes: 97.5%, longer windows, exponential
   weighting, or fat-tailed parametric distributions.

## My check questions (2026-11-23)

1. **Q:** On the stressed window, historical ES 97.5% (2.88 L) is below VaR 99% (3.41 L).
   How?
   **My answer:** The effect of fat tails is concentrated in very few days.
   **Feedback:** Right. ES 97.5% averages 7 days; the 3 worst average 3.77 L but
   days 4–7 only ~2.21 L, pulling the average below the 3rd-worst day.
2. **Q:** Parametric ES/VaR is 1.15 every day. Why is that useless for learning about
   fat tails?
   **My answer:** Parametric VaR is a formula, so it doesn't take the worst of the
   worst into account.
   **Feedback:** Right. It uses only μ and σ; the bell curve fixes the tail shape
   (2.665 / 2.326 = 1.15). A crash can only inflate σ, never fatten the tail
   relative to the middle.
3. **Q:** Historical ES 99% averages just 3 days. Weakness?
   **My answer:** One inflated value may affect the number a lot.
   **Feedback:** Right: high variance from a tiny sample (like a 3-row test set).
   Fixes: 97.5%, longer windows, exponential weighting, fat-tailed distributions.

## Next phase

**Phase 8: EWMA volatility VaR.** Give recent days more weight than old ones
(FRAM slides 23–30: "Responsive VaR", "Exponential weighting"), so VaR reacts
faster when volatility jumps. This targets the 2020 breach cluster from Phase 4 and
the ghost-effect cliffs from Phase 2.
