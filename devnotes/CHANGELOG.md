# Changelog

One line per phase, newest first.

- 2026-11-24: Phase 11 addendum: ν sensitivity table (nu_sensitivity in run_monte_carlo.py): ν 3–6 pass Kupiec (43–50 breaches), ν ≥ 8 fail (63+). Rolling 250-day MLE fit of ν did worse (60 breaches; calm windows ν ≈ 13). ν = 5 kept as a documented assumption.

- 2026-11-24: Phase 11: Monte Carlo VaR (models/monte_carlo.py: Cholesky, 10,000 draws, normal or Student-t ν 5, fixed seed). Full period (4,756 days): MC-normal = parametric (82 breaches, daily ratio 0.987–1.021); MC-t 45 breaches (Kupiec p 0.71) but still bunches (independence p 0.0088). Sampling noise 7.0% / 2.4% / 0.9% at 1k / 10k / 100k draws. Stage 3 complete. run_monte_carlo.py.

- 2026-11-24: Phase 10 (Stage 3): Christoffersen independence and conditional-coverage tests (backtest.christoffersen, longest_run) on all 6 models over 4,506 days. No model passes conditional coverage (responsive p 0.045, FHS 0.044); only EWMA (p 0.19) and parametric (0.054) pass independence. Back-to-back breaches are shared market events (Infosys Aug 2017, 4 Oct 2018, Mar 2020, Apr 2025). run_garch.py refactored (model_setup, six_model_forecasts); run_christoffersen.py.

- 2026-11-24: Phase 9: GARCH(1,1) VaR via `arch` (normal tail and Filtered Historical Simulation), re-fitted every 21 days with parameters held between (rolling_garch); compare_models shared scoring. 6-model backtest (4,506 days): GARCH-FHS 53 breaches (p 0.25, pass), GARCH-normal 70 (reject); responsive still best (47). Found daily re-fit flips (α 0.00→0.22→0.04, VaR −41%) and α ≈ 0 fits in 24/215 calm windows (limitation). run_garch.py; arch added to requirements.

- 2026-11-23: Phase 8: EWMA (RiskMetrics λ 0.94) and Responsive VaR (weighted HS, λ 0.994, 500 days) behind the same interface; exp_weights, weighted_age. Common-period backtest (4,505 days): responsive 47 breaches vs 45.1 expected (Kupiec p 0.77), fewest in 2020 (6); EWMA has no cliffs (−3%) but 76 breaches. run_responsive.py.

- 2026-11-23: Phase 7 (Stage 2): Expected Shortfall: predict_es on every model (historical tail average, parametric σφ(z)/(1−α)−μ), ES 99% and 97.5%, stressed ES (hist. ₹3.77 L), ES size check on breach days (ES 11% / 24% too small). run_es.py.

- 2026-11-23: Phase 6: Stage 1 complete. Final results-first README (headline table, method, limitations, planned next), all five scripts verified end to end, comment tidy-up, resume bullets in devnotes/phase-6-ship-it.md.

- 2026-11-23: Phase 5: automated Excel breach report (Summary, Breach Log with driver asset, 2 native charts, Chart Data); 146 breaches logged, single stocks drove 135 (Infosys 55, Reliance 51). report.py.

- 2026-11-23: Phase 4: backtesting over 4,755 days: historical 64 breaches (Kupiec p = 0.023; green today, never red), parametric 82 (p = 5.3e-06; amber today, red 5.1% of days). backtest.py, run_backtest.py.

- 2026-11-23: Phase 3: stressed VaR on the worst 250-day window (picked by highest historical VaR): COVID (₹3.41 L hist., 3.1× today) beats 2008 (₹2.64 L); parametric dilutes COVID (₹1.51 L). stressed.py, run_stressed.py.

- 2026-11-18: Phase 2: historical-simulation and parametric VaR behind one VaRModel interface, rolling 250-day window (4,752 daily forecasts from 2 Sep 2008); load_data() pipeline helper; run_var.py.

- 2026-11-18: Phase 1: data layer (prices → returns → ₹ P&L), one-at-a-time download, automatic glitch cleaning (5 USD/INR prints removed), gold as COMEX × USD/INR so data starts 18 Sep 2007 and includes 2008; 5,002 trading days.

- 2026-11-18: Setup: folder cleaned (unrelated work archived), packages installed, project skeleton, git repo initialised.
