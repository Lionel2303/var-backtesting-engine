# Study guide: the whole project on a few pages

A revision map for Phases 1–11. Every number comes from the phase devnotes; follow
the links for the full worked examples. Suggested order:
1. Read sections 1–3.
2. Do the self-test (section 6) without looking.
3. Re-read the devnote for any question you missed.

---

## 1. The story in seven sentences

1. **VaR** = the loss you exceed on only 1% of days. On ₹60 L it's about ₹1.1 L
   today ([Phase 2](phase-2-var-models.md)).
2. Real losses have **fat tails**, so bell-curve models break too often:
   - parametric: 82 breaches vs 47.6 expected
   - historical: 64 ([Phase 4](phase-4-backtesting.md))
3. The worst year for this portfolio was **COVID, not 2008** (stressed VaR ₹3.41 L,
   [Phase 3](phase-3-stressed-var.md)).
4. **ES** asks how bad the bad days are: historical ES ₹1.41 L, 1.27× VaR
   ([Phase 7](phase-7-expected-shortfall.md)).
5. **Weighting recent days** makes VaR react faster:
   - Responsive VaR: 47 breaches, the best model ([Phase 8](phase-8-responsive-var.md))
   - **fitting** the dynamics (GARCH, [Phase 9](phase-9-garch.md)) works only with
     a fat tail (FHS 53 vs normal 70)
6. **Breach timing matters**, not just the count. No model passes Christoffersen's
   joint test ([Phase 10](phase-10-christoffersen.md)).
7. **Monte Carlo** with fat-tailed draws (t, ν = 5) fixes the count, 82 → 45. It
   doesn't fix timing ([Phase 11](phase-11-monte-carlo.md)).

---

## 2. Every model on one page

| Model | Phase | Idea in one line | Breaches (expected) | Verdict |
|---|---|---|---|---|
| Historical simulation | 2 | Replay the last 250 days; VaR = 3rd-worst | 64 (47.6)¹ | Narrow Kupiec fail; never red |
| Parametric | 2 | VaR = 2.326σ − μ (bell curve) | 82 (47.6)¹ | Fails: thin tails |
| Stressed VaR | 3 | Historical VaR on a **fixed** worst window (COVID) | — | ₹3.41 L, 3.1× today |
| Expected Shortfall | 7 | Average loss beyond VaR | — | Historical ES 11% too small on breach days |
| EWMA | 8 | Parametric with weights λ = 0.94 (half-life 11 days) | 76 (45.1)² | Fastest reaction, forgets fast, fails Kupiec |
| Responsive (weighted HS) | 8 | Historical with λ = 0.994 on 500 days | **47 (45.1)²** | **Best count**; fails independence narrowly |
| GARCH(1,1) normal | 9 | σ² = ω + αr² + βσ², fitted; normal tail | 70 (45.1)² | Fails: thin tail; α = 0 fits froze it in 2020 |
| GARCH-FHS | 9 | GARCH σ × the data's own standardised surprises | 53 (45.1)² | Passes Kupiec; unstable parameters |
| MC-normal | 11 | 10,000 simulated days, bell-curve draws | 82 (47.6)¹ | = parametric, breach for breach |
| MC-t (ν = 5) | 11 | Same, fat-tailed draws | **45 (47.6)¹** | Passes Kupiec; still bunches |

¹ Full period, 2 Sep 2008 → Nov 2026 (4,755–4,756 days).
² Common period, 18 Aug 2009 → Nov 2026 (4,505–4,506 days). This one starts later
because the 500-day models need a longer history.

**The four tests:**

| Test | Question | Phase |
|---|---|---|
| Kupiec POF | Is the **number** of breaches about 1%? | 4 |
| Basel traffic light | How many breaches in the last 250 days? Green 0–4, amber 5–9, red 10+ | 4 |
| ES size check | On breach days, was the loss about the size ES predicted? | 7 |
| Christoffersen | Are breaches **independent** (not back to back)? Joint test = count + independence | 10 |

---

## 3. Formula sheet, each with a tiny example

| Concept | Formula | Example |
|---|---|---|
| Historical VaR (99%, 250 days) | VaR = 3rd-worst P&L | Illustration: worst three days −₹2.0 L, −₹1.6 L, −₹1.3 L → VaR ₹1.3 L |
| Parametric VaR | z·σ − μ, z = 2.326 | σ = ₹50,000, μ = 0 → ₹1.16 L |
| Normal ES (99%) | σ·φ(z)/(1−α) = 2.665σ | σ = ₹50,000 → ₹1.33 L |
| Portfolio σ | √(wᵀ Σ w) | ₹10 L each, vols 2% and 1%, ρ 0.3 → ₹24,900, not ₹30,000 (diversification) |
| Exponential weight | λ^(days back), normalised | λ 0.94: yesterday 6.0%, 10 days ago 3.2% (equal weights: 0.4%) |
| Half-life | ln 0.5 / ln λ | 0.94 → 11 days; 0.994 → 115 days |
| GARCH(1,1) | σ²ₜ₊₁ = ω + α·r²ₜ + β·σ²ₜ | ω .02, α .07, β .89, σ 0.7%: calm day → 0.69%; −5% day → **1.48%** |
| GARCH with α = 0 | the r² term disappears | after a −5% day: σ² = 0.003 + **0**×25 + 0.994×0.436 → σ stays 0.66% (blind) |
| FHS | VaR = −(1%-worst ε) × σₜ₊₁ | 5th-worst ε of 500 = −2.55, σ ₹42,000 → ₹1.07 L |
| Kupiec | LR = −2 ln(L(1%) / L(observed rate)) ~ χ²(1) | 250 days: 3 breaches p 0.76 pass; 10 breaches p 0.0003 reject |
| Christoffersen | Compare π11 (after a breach) with π01 (after a calm day) | 5 spread breaches p 0.65; 5 in a row: π11 80%, p 2.6×10⁻⁸ |
| Cholesky | Σ = LLᵀ; returns = μ + Lz | L = [[1,0],[1,1.732]], z = (−2, 0.5) → (−2.0%, −1.13%) |
| Monte Carlo noise | spread ∝ 1/√N | 1k: 7.0%, 10k: 2.4%, 100k: 0.9%; 10× less noise needs 100× the draws |
| Student-t 1% point (unit variance) | t.ppf(0.99, ν)·√((ν−2)/ν) | ν 5 → 2.61σ vs normal 2.33σ (+12%) |

---

## 4. Pairs that are easy to mix up

These come from the check questions I got wrong. Each pair gets a one-line test.

| This… | …is not this | One-line test |
|---|---|---|
| **σ (volatility)**: how big a normal day is | **ν (tail shape)**: how often extreme days happen | Same σ, different ν: MC-normal and MC-t had the same σ (₹45,650) but 82 vs 45 breaches |
| **Kupiec**: how many breaches | **Christoffersen**: when they happen | Parametric fails Kupiec but passed independence; responsive is the reverse |
| **Weights changed** | **Test period changed** | Historical passed Kupiec in Phase 8 only because 2008–09 was dropped (64 → 58) |
| **Sampling noise** (random, averages out) | **Fat tail** (systematic, always raises VaR) | MC-normal / parametric averaged 1.004; MC-t / MC-normal 1.122 |
| **Equal weights** (historical: every day 0.4%) | **Recency weights** (EWMA: yesterday 6%) | Historical cannot "over-weight yesterday", it weights every day the same |
| **Fixing the tail** (FHS, t) | **Fixing the speed** (EWMA, GARCH) | MC-t fixed the count (45) but not bunching (independence p 0.0088) |
| **Fitting on past data** (legitimate) | **Choosing by backtest result** (tuning on the test set) | Picking ν = 5 because it gave 45 breaches would be peeking |
| **VaR**: where the tail starts | **ES**: average inside the tail | Historical 1.11 L vs 1.41 L |
| **Stressed VaR**: fixed crisis window | **VaR**: rolling recent window | COVID window gives ₹3.41 L regardless of today |

---

## 5. Five lessons that cut across phases

1. **Fat tails beat everything built on a bell curve.** Each fix worked the same way:
   - historical vs parametric (64 vs 82)
   - FHS vs GARCH-normal (53 vs 70)
   - MC-t vs MC-normal (45 vs 82)
2. **Speed vs memory.** Fast models react but forget:
   - EWMA was back to ₹1.16 L by Sep 2020
   - slow models remember but fall off a cliff when the crisis leaves the window
     (historical −28% in one day, Mar 2021)
3. **Short calm samples can't see rare events.**
   - GARCH fitted α = 0 in 24 of 215 windows
   - a fitted ν was about 13 in calm years
   - both made VaR too low before a crash
4. **A verdict depends on the test period.** Always state the dates.
5. **The count and the timing are separate problems with separate fixes.**
   - tail shape fixes the count
   - reaction speed fixes the timing
   - no single model here fixed both

---

## 6. Self-test

Answer each one out loud first, then check the answers in section 7.

1. Why did parametric VaR peak after a big **gain** in May 2009?
2. Why is the stressed window COVID, not 2008, and why does it matter?
3. 10 breaches in 250 days: which zone, and roughly what Kupiec p?
4. Why can 97.5% ES be lower than 99% VaR?
5. What is the "ghost effect", and which model avoided it?
6. What does α+β tell you in GARCH? Full-history value?
7. Why did GARCH-normal VaR sit at ₹0.92 L through 9–23 Mar 2020?
8. GARCH-normal and GARCH-FHS use the same σ. Why 70 vs 53 breaches?
9. What is π11, and which model had the lowest?
10. Name one blind spot of the Christoffersen test.
11. Why build Monte Carlo if MC-normal = parametric?
12. Is the MC-t result reliable? One sentence.

---

## 7. Answers

1. σ counts gains and losses alike. The +₹6.0 L election-rally day raised σ, so the
normal model treated a big gain as risk. Phase 2.

2. The window is chosen by searching for the highest historical VaR: COVID ₹3.41 L vs
2008 ₹2.64 L. Assuming "2008 is the worst" would understate SVaR by about 23%.
Phase 3.

3. Red (10+). p ≈ 0.0003, a clear reject. Phase 4.

4. They're different points in the tail. On the COVID window ES 97.5% was ₹2.88 L vs
SVaR ₹3.41 L. Averaged over 18 years they're about equal (ES 97.5% / VaR 99% ≈
1.01). Phase 7.

5. VaR drops sharply when an old crisis leaves the window, with no change in the
market. Historical fell 28% in one day (Mar 2021); EWMA's worst one-day drop was
only 3%. Phase 8.

6. Persistence: how long a shock lasts. 0.987 means a half-life of 53 days. EWMA has
α+β = 1: no pull back to a long-run level. Phase 9.

7. The parameters fitted on 4 Mar had α = 0.000 and were held for 21 days. With α = 0
the model ignores today's return. Phase 9.

8. The tail. FHS's 1% cutoff comes from real standardised surprises (about 2.5σ), not
2.33σ. Phase 9.

9. The chance of a breach the day after a breach. EWMA had the lowest at 3.95%:
yesterday's loss weighs 6%, so VaR rises immediately. Phase 10.

10. It only looks one day back. Breaches a few days apart in a crisis look independent.
Use a duration test (days between breaches) or a rolling count. Phase 10.

11. Flexibility. Swap the distribution in one line (t: 82 → 45), re-price options on
each simulated day, and handle many factors or multi-day paths. Phase 11.

12. For the count, yes: it passes Kupiec for any ν from 3 to 6, fails from 8. For
timing, no: independence p 0.0088. ν is a documented assumption. Phase 11.
