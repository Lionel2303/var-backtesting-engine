# Phase 5: Automated Excel breach report

_Completed 2026-11-23. Every number below comes from running `python report.py` on
2026-11-23 (data up to 2026-11-23) and reading the saved workbook back._

## Goal

Turn Phases 2–4 into the **daily deliverable** a market risk team sends: one Excel
workbook, built by code, that says what VaR is, whether yesterday's forecast held,
how the models are doing in the backtest, and which asset drove each breach.

**Why a Market Risk team cares:** the numbers only matter if they reach the desk
and the managers every morning, correctly and on time. Daily VaR / breach
reporting is the core of the role this project mirrors.

## Concepts

### What goes in a breach report
| Sheet | Shows | Reader |
|---|---|---|
| Summary | Latest day: forecast vs actual P&L, breach yes/no. Per model: next-day VaR, stressed VaR, breaches, Kupiec, Basel zone | Manager: "are we OK?" |
| Breach Log | One row per breach: date, model, VaR, P&L, loss beyond VaR, driver asset, every asset's P&L | Analyst: "what happened?" |
| Charts | P&L vs −VaR, last 250 days and full history; breaches as red dots | Everyone: see it at a glance |
| Chart Data | The numbers behind the charts | Anyone checking the chart |

### Two different VaR numbers on one page
- **"VaR forecast for this day"** is the forecast *for* 23 Nov, built from the 250
  days ending 20 Nov. It's compared with 23 Nov's actual P&L.
- **"VaR for next trading day"** is the forecast for 24 Nov, built from the 250 days
  ending 23 Nov.
- Parametric: ₹1,08,361 → ₹1,08,746, because the window slid one day. Historical:
  ₹1,10,728 in both. The 3rd-worst day of the window didn't change (historical VaR
  moves in steps).

### Breach driver
For each breach day, the **driver** is the asset with the biggest rupee loss that
day (`idxmin` of the six asset P&Ls).
- 12 Apr 2013: Infosys −₹2,12,586 on a portfolio loss of −₹2,60,007. One stock
  fell (results day), so this is **idiosyncratic** risk.
- 23 Mar 2020: Reliance −₹1,31,539 on a loss of −₹4,19,227. Everything fell
  together, so this is **systematic** risk, and Reliance was just the worst of six
  bad assets.
- **Caveat:** this is a simple rule, not formal risk attribution. Component VaR
  (each asset's contribution to VaR) is a Later Stage item.

### Why automate
- **Fewer errors:** no copy-paste slips.
- **Reproducible:** a validator or regulator can rerun the script and get the same
  workbook (model governance).
- **Fast:** done before the market opens.
- **Scales:** one script, any number of portfolios.

**ML link:** it's like writing a training/evaluation script instead of clicking
through a notebook. The report is the "evaluation dashboard" for the VaR models.

## Code walkthrough

| File / function | Takes | Returns | Why it's written this way |
|---|---|---|---|
| `report.py` → `build_results()` | — | dict: `var`, `asset_pnl`, `models`, `breach_log`, `stress` | Runs the pipeline once and reuses Phases 2–4 code (`rolling_var`, `find_breaches`, `kupiec_pof`, `rolling_zone`, `find_stress_window`). No new risk maths |
| `style_header_row(ws, row)` | sheet, row number | — | One look for every header (dark blue, white bold) |
| `set_widths(ws, widths)` | sheet, {col: width} | — | Readable columns |
| `write_summary(ws, res)` | sheet, results | — | Latest day + validation table; zone cell filled green/amber/red |
| `write_breach_log(ws, res)` | sheet, results | — | Newest first; frozen header; filter arrows |
| `write_chart_data(ws, res)` | sheet, results | last row number | −VaR is written *negative* so it sits on the loss side with P&L; breach column is blank except on breach days |
| `add_line_chart(...)` | chart sheet, data sheet, row range, title, anchor cell | — | Native Excel chart (zoomable, editable), not a pasted image |
| `main()` | — | saves `outputs/var_breach_report_<date>.xlsx` | The file name carries the data date, so old reports aren't overwritten |

**Library functions used for the first time (openpyxl):**
- `Workbook()`, `wb.active`, `wb.create_sheet(name)`, `wb.save(path)`: create,
  add sheets, save.
- `ws.append([...])`: write a list as the next row.
- `cell.number_format = '"₹"#,##0;[Red]-"₹"#,##0'`: *display* format only; the
  stored value stays exact (110727.64 shows as ₹110,728).
- `PatternFill("solid", fgColor=...)`, `Font(bold=True)`, `Alignment(...)`: cell
  styling.
- `ws.freeze_panes = "A2"`, `ws.auto_filter.ref = ws.dimensions`: frozen header,
  filter arrows.
- `LineChart()`, `Reference(...)`, `chart.add_data`, `chart.set_categories`,
  `SeriesLabel(v=name)`: a chart, the cells it reads, the x-axis dates, legend names.
- `get_column_letter(3)` → "C".
- pandas `idxmin()`: the label (here, the asset) of the smallest value.

## Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| Output format | Excel (openpyxl) | PDF, HTML, CSV | What risk teams actually email; filterable; charts stay editable |
| Charts | Native Excel charts | matplotlib PNG pasted in | Zoomable and editable in Excel; no image files |
| Breach driver | Asset with the biggest loss that day | Component VaR / marginal VaR | Simple and explainable; formal attribution is a Later Stage |
| Breach dots on chart | Historical model only | Both models | Two sets of dots on 4,755 days is unreadable; both models are in the Breach Log |
| Report in git | Not committed (`outputs/`, `*.xlsx` ignored) | Commit each report | Generated output; anyone can rebuild it with one command |
| Labels | "VaR forecast for this day" vs "VaR for next trading day" | One "VaR today" column | The first version was ambiguous (see Bugs) |

## Results (run of 2026-11-23)

Workbook: `outputs/var_breach_report_2026-11-23.xlsx`, 4 sheets.

**Summary sheet**
| | Historical | Parametric |
|---|---|---|
| VaR forecast for 23 Nov | ₹1,10,728 | ₹1,08,361 |
| Actual P&L 23 Nov | −₹44,206 (no breach) | −₹44,206 (no breach) |
| VaR for next trading day | ₹1,10,728 | ₹1,08,746 |
| Stressed VaR (10 Apr 2019 → 23 Mar 2020) | ₹3,41,468 | ₹1,51,291 |
| Breaches / expected | 64 / 47.6 (1.35%) | 82 / 47.6 (1.72%) |
| Kupiec LR, p-value | 5.19, 0.023 → REJECT | 20.72, 5.3e-06 → REJECT |
| Breaches in last 250 days, zone | 3, **GREEN** | 7, **AMBER** |

**Breach Log:** 146 rows (64 + 82). Which asset drove the breach:

| Driver | Historical | Parametric | Total |
|---|---|---|---|
| Infosys | 24 | 31 | 55 |
| Reliance | 24 | 27 | 51 |
| HDFC Bank | 12 | 17 | 29 |
| Gold (₹) | 3 | 5 | 8 |
| Nifty 50 | 1 | 2 | 3 |
| USD/INR | 0 | 0 | 0 |

- Single stocks drive 93% of breaches (135 of 146). Nifty, already a 50-stock
  basket, almost never does. USD/INR never does: it tends to rise when stocks fall
  (the natural hedge).
- Median loss beyond VaR on a breach day: 18% (historical), 16% (parametric).
- Biggest examples: 12 Apr 2013, historical VaR ₹86,625, loss ₹2,60,007 (200%
  beyond; driver Infosys). 23 Mar 2020, parametric VaR ₹1,36,199, loss ₹4,19,227
  (208% beyond; driver Reliance).

**Charts:** 2 line charts (last 250 days; full history), 64 red breach dots on the
full-history chart.

**Note on live data:** an earlier run the same day showed 23 Nov P&L as −₹38,249 and
next-day parametric VaR ₹1,08,675. Yahoo updated that day's closing prices between
runs. The latest day can change until the data settles.

## Bugs and fixes

1. **Chart legend names.** A 250-day slice of the data doesn't include the header
   row, so `titles_from_data=True` would have used a P&L number as a name. **Fix:**
   `titles_from_data=False` and name each series with `SeriesLabel`.
2. **Ambiguous labels.** The first Summary showed two different "VaR today" numbers.
   **Fix:** relabelled as "VaR forecast for this day" (compared with today's P&L) and
   "VaR for next trading day".
3. **Read-back check failed on dates.** openpyxl reads dates back as `datetime`,
   not `date`, so the verification script's comparison missed. The fix was in the
   check script (compare `.date()`); the report itself was correct.

## Interview questions (with model answers)

1. **What's in your daily VaR report?**
   A summary (latest forecast vs actual P&L, breach flag, next-day VaR, stressed
   VaR, breach count vs expected, Kupiec p-value, Basel zone), a breach log with the
   asset that drove each loss, and VaR-vs-P&L charts. All built by one script from
   the same code as the backtest.
2. **Which assets drove your breaches, and what does that tell you?**
   Of 146 breaches, Infosys drove 55 and Reliance 51; single stocks drove 135. Most
   breaches come from single-stock moves (concentration). USD/INR never drove one,
   because it's a natural hedge.
3. **Why automate the report?**
   No manual errors, reproducible for validation and audit, ready before the market
   opens, and it scales to many portfolios.
4. **How is your "driver" different from component VaR?**
   The driver is simply the worst asset on the breach day (after the fact).
   Component VaR splits the VaR forecast into each asset's contribution, including
   correlations (before the fact). Mine is the simpler, explainable version.
5. **Why is the report generated, not committed to git?**
   It's output, not source. The code plus the data reproduce it exactly, and
   committing daily workbooks would bloat the repo.

## My check questions (2026-11-23)

1. **Q:** 12 Apr 2013 was driven by Infosys, 23 Mar 2020 by Reliance. What's the
   difference between those two kinds of bad day?
   **My answer:** Infosys crashed alone, while everything fell in March 2020.
   **Feedback:** Correct. The first is idiosyncratic (one company's news, which
   diversification softens); the second is systematic (correlations rise,
   diversification barely helps).
2. **Q:** Why do parametric's "VaR forecast for this day" and "VaR for next trading
   day" differ?
   **My answer:** They forecast different days.
   **Feedback:** Correct. The windows end on 20 Nov and 23 Nov, sliding one day.
   Historical showed the same number in both, because its 3rd-worst day didn't
   change.
3. **Q:** Two reasons to build the report automatically rather than by hand?
   **My answer:** Don't know.
   **Feedback:** Explained with the example of a pasted wrong column. Four reasons:
   fewer errors, reproducibility/audit, speed before the market opens, scale.

## Next phase

**Phase 6: Ship it.** Final README (problem, method, results with real numbers, how
to run), a code tidy-up pass, and 2–3 resume bullets using only the results in these
devnotes.
