# Phase 6: Ship it (final README, code tidy, resume bullets)

_Completed 2026-11-23. All five scripts were run end to end on 2026-11-23 (data up
to 2026-11-23) with no errors; every number in the README comes from those runs._

## Goal

Turn five working phases into a finished project that someone else can read in two
minutes: a README that leads with results, clean code, and resume bullets that use
only real numbers.

**Why a Market Risk team cares:** a model nobody can understand or rerun can't be
validated. Clear documentation and reproducible results are part of model
governance, not decoration.

## Concepts

### Lead with the result
A recruiter reads the top of the README and stops. So the README opens with a
headline results table and a one-paragraph verdict. The method and per-phase
details come after.

### Every number must be traceable
Each figure in the README and in the resume bullets appears in a devnote and in
the output of a script run on 2026-11-23. Example: "64 breaches vs 47.6 expected"
→ `python run_backtest.py` → devnotes/phase-4-backtesting.md.

### Say what the model can't do
A Limitations section: constant exposure, the simple breach-driver rule, Kupiec's
blindness to clustering, free data that can revise the latest day. Interviewers
trust a candidate who knows the weak spots.

### Why "COVID beat 2008" matters (check question 3)
SVaR on 2008 = ₹2.64 L; SVaR on the true worst window (COVID) = ₹3.41 L. Assuming
2008 would understate SVaR by ₹0.77 L (about 23%). Basel 2.5 capital is VaR plus
SVaR, each times a multiplier of at least 3, so the bank would hold too little
capital for the very crisis SVaR is meant to cover. The lesson: the stress window
must be **searched for** for each portfolio and re-checked when positions change,
not assumed.

## Code walkthrough

No new functions. Changes:
| File | Change | Why |
|---|---|---|
| `config.py`, `data.py` | 3 comments: "Part 1/2/3" → "Phase 1/2/3" | Leftover wording from before the project used phases |
| `README.md` | Rewritten: headline results, portfolio, method, results by phase, limitations, planned next, how to run, structure | Final, results-first version |

End-to-end check: `data.py`, `run_var.py`, `run_stressed.py`, `run_backtest.py`
and `report.py` all exit with code 0.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| README order | Results first, method after | Method first | Readers decide in the first screen |
| Phase 1/2 numbers | Refreshed to the 2026-11-23 run (5,005 days; mean ₹2,994, std ₹53,120) | Keep the 2026-11-18 figures | One consistent run date across the README |
| Chart image in README | Not added | Commit one PNG | Keeps the "no generated outputs in git" rule; can be added later in one commit |
| Resume bullets | Stored here, not in the README | In the README | The README describes the project; bullets are for my resume |

## Results (run of 2026-11-23)

| | Historical | Parametric |
|---|---|---|
| Next-day VaR | ₹1.11 L (1.85%) | ₹1.09 L (1.81%) |
| Stressed VaR (COVID window) | ₹3.41 L (3.1× today) | ₹1.51 L |
| Breaches / expected (4,755 days) | 64 / 47.6 | 82 / 47.6 |
| Kupiec p-value | 0.023 (reject at 5%) | 5.3e-06 (reject) |
| Zone today | Green (3) | Amber (7) |
| Red-zone days | 0% | 5.1% |

Data: 5,005 trading days (18 Sep 2007 → 23 Nov 2026); 5 USD/INR glitches removed.

### Resume bullets (only real numbers)

**VaR Model Validation & Backtesting Engine** (Python, pandas, NumPy, SciPy, openpyxl)
- Built a Python engine computing 1-day 99% VaR (historical simulation, parametric)
  and Basel 2.5-style stressed VaR for a ₹60 lakh, 6-asset Indian portfolio over 18
  years. Found COVID, not 2008, to be the worst stress window (SVaR ₹3.41 L, 3.1×
  current VaR).
- Backtested 4,755 daily forecasts with the Kupiec POF test and Basel traffic
  light. Historical simulation: 64 breaches vs 47.6 expected, never in the red
  zone. Parametric: 82 breaches (p ≈ 5×10⁻⁶) and 5% of days in red, showing
  fat-tail risk underestimation.
- Automated a daily Excel breach report (summary, Kupiec/traffic-light status, a
  146-row breach log tracing each loss to its driving asset, VaR-vs-P&L charts).
  Single stocks drove 135 of 146 breaches. Built a data-quality filter that
  auto-removed 5 bad price prints while keeping real crisis days.

## Bugs and fixes

None this phase. The full end-to-end run passed first time.

## Interview questions (with model answers)

1. **Walk me through your project in one minute.**
   I built a VaR engine for a ₹60 lakh Indian portfolio covering stocks, the Nifty,
   gold and USD/INR. It produces two VaR models on a rolling 250-day window and
   stressed VaR on the worst historical year. I backtested 18 years of forecasts
   with Kupiec and the Basel traffic light, and it generates a daily Excel breach
   report. The key finding: the normal-distribution model badly underestimates
   risk (82 breaches vs 47.6), while historical simulation is close (64, never
   red).
2. **Your historical model failed Kupiec. Why call it the better model?**
   It's a narrow rejection (p = 0.023), which would pass at the 1% level, and it
   was never red and is green today. Parametric fails decisively (p ≈ 5×10⁻⁶) and
   was red 5% of days.
3. **What would you improve first?**
   Breach clustering in 2020 (8 and 11 breaches) shows the models react too
   slowly. I'd add EWMA/GARCH volatility, Expected Shortfall for tail size, and the
   Christoffersen test to measure clustering.
4. **Why did you find COVID worse than 2008?**
   The worst window depends on the portfolio. Mine holds Indian single stocks, and
   March 2020 had the four worst days in the data (down to −₹4.19 L). Assuming 2008
   would have understated stressed VaR by about 23%.
5. **How do you know your numbers are right?**
   Each step was checked by hand (Kupiec on 0/3/10 breaches, the 3rd-worst-of-250
   rule, breach-rule edge cases). The data glitch filter logs every price it
   removes. Every script reruns from raw data with one command.

## My check questions (2026-11-23)

1. **Q:** Your historical model failed Kupiec. Why still call it the better model?
   **My answer:** It was tested on ~4,700 rows, of which only ~65 were breaches vs
   84 for parametric; it failed Kupiec only marginally.
   **Feedback:** Right idea. Use exact numbers (4,755 days, 64 vs 82, 47.6
   expected). Quantify "marginally" (p = 0.023 passes at 1%), and add the traffic
   light: never red, green today, vs parametric red 5.1%.
2. **Q:** What does Kupiec miss, using the 2020 numbers?
   **My answer:** Kupiec misses clustering.
   **Feedback:** Correct. 2020 had 8 / 11 breaches vs ~2.5 expected; Kupiec sees
   only the 18-year total. The Christoffersen independence test checks whether a
   breach makes the next one more likely.
3. **Q:** Why is "COVID beat 2008" useful to a risk manager?
   **My answer:** Not sure.
   **Feedback:** Explained with numbers: assuming 2008 understates SVaR by ₹0.77 L
   (~23%), which means too little Basel 2.5 capital. The stress window must be
   searched for for each portfolio.

## Next phase

**Stage 1 is complete.** Next (no date set): Stage 2, Expected Shortfall and
GARCH/EWMA volatility, which directly target the fat tails and slow reaction found
in the backtest.
