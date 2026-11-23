# Changelog

One line per phase, newest first.

- 2026-11-23: Phase 3: stressed VaR on the worst 250-day window (picked by highest historical VaR): COVID (₹3.41 L hist., 3.1× today) beats 2008 (₹2.64 L); parametric dilutes COVID (₹1.51 L). stressed.py, run_stressed.py.

- 2026-11-18: Phase 2: historical-simulation and parametric VaR behind one VaRModel interface, rolling 250-day window (4,752 daily forecasts from 2 Sep 2008); load_data() pipeline helper; run_var.py.

- 2026-11-18: Phase 1: data layer (prices → returns → ₹ P&L), one-at-a-time download, automatic glitch cleaning (5 USD/INR prints removed), gold as COMEX × USD/INR so data starts 18 Sep 2007 and includes 2008; 5,002 trading days.

- 2026-11-18: Setup: folder cleaned (unrelated work archived), packages installed, project skeleton, git repo initialised.
