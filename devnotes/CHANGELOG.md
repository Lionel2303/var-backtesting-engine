# Changelog

One line per phase, newest first.

- 2026-11-23: Phase 6: Stage 1 complete. Final results-first README (headline table, method, limitations, planned next), all five scripts verified end to end, comment tidy-up, resume bullets in devnotes/phase-6-ship-it.md.

- 2026-11-23: Phase 5: automated Excel breach report (Summary, Breach Log with driver asset, 2 native charts, Chart Data); 146 breaches logged, single stocks drove 135 (Infosys 55, Reliance 51). report.py.

- 2026-11-23: Phase 4: backtesting over 4,755 days: historical 64 breaches (Kupiec p = 0.023; green today, never red), parametric 82 (p = 5.3e-06; amber today, red 5.1% of days). backtest.py, run_backtest.py.

- 2026-11-23: Phase 3: stressed VaR on the worst 250-day window (picked by highest historical VaR): COVID (₹3.41 L hist., 3.1× today) beats 2008 (₹2.64 L); parametric dilutes COVID (₹1.51 L). stressed.py, run_stressed.py.

- 2026-11-18: Phase 2: historical-simulation and parametric VaR behind one VaRModel interface, rolling 250-day window (4,752 daily forecasts from 2 Sep 2008); load_data() pipeline helper; run_var.py.

- 2026-11-18: Phase 1: data layer (prices → returns → ₹ P&L), one-at-a-time download, automatic glitch cleaning (5 USD/INR prints removed), gold as COMEX × USD/INR so data starts 18 Sep 2007 and includes 2008; 5,002 trading days.

- 2026-11-18: Setup: folder cleaned (unrelated work archived), packages installed, project skeleton, git repo initialised.
