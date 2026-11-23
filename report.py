"""
report.py — Phase 5: automated Excel breach report.

    python report.py      -> outputs/var_breach_report_<last data date>.xlsx

The daily deliverable of a market risk team, built automatically:
    Summary     latest day (VaR vs P&L, breach?), and per model: next-day VaR,
                stressed VaR, breaches, Kupiec test, Basel traffic light
    Breach Log  every breach: date, model, VaR, P&L, size, driving asset
    Charts      VaR vs actual P&L (last 250 days and full history)
    Chart Data  the numbers behind the charts

No new risk maths here: it reuses Phases 2-4 (models, stressed.py, backtest.py).
"""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook                      # creates Excel files
from openpyxl.chart import LineChart, Reference    # native Excel charts
from openpyxl.chart.series import SeriesLabel      # a chart line's legend name
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter        # 1 -> "A", 2 -> "B", ...

from backtest import find_breaches, kupiec_pof, rolling_zone
from config import CONFIDENCE, HOLDINGS, WINDOW
from data import load_data
from models import HistoricalVaR, ParametricVaR, rolling_var
from stressed import find_stress_window, stressed_var

OUTPUT_DIR = Path("outputs")

# Excel number format: rupees with thousands separators, negatives in red.
# e.g. 111000 -> ₹111,000   and   -40000 -> -₹40,000 (red)
RUPEE = '"₹"#,##0;[Red]-"₹"#,##0'
# Background colours (hex RGB) for the traffic-light zones and headers.
ZONE_FILL = {"green": "C6EFCE", "amber": "FFEB9C", "red": "FFC7CE"}
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")   # dark blue
HEADER_FONT = Font(bold=True, color="FFFFFF")          # white bold text
# Legend names for the 4 chart lines (same order as the Chart Data columns 2-5).
SERIES_NAMES = ["Actual P&L", "-VaR historical", "-VaR parametric", "Breach (historical)"]


# ---------------------------------------------------------------------------
# PART 1 — compute everything the report shows
# ---------------------------------------------------------------------------
def build_results():
    """
    Run the whole pipeline once and collect every number the report needs.

    Returns a dict with:
        var         : table of daily VaR forecasts per model + actual P&L
        asset_pnl   : rupee P&L per asset per day (to find breach drivers)
        models      : per-model summary (VaR, SVaR, breaches, Kupiec, zone)
        breach_log  : one row per breach, newest first
        stress      : the stressed window's dates
    """
    data = load_data()
    returns, pnl = data["returns"], data["pnl"]
    models = [HistoricalVaR(HOLDINGS, CONFIDENCE), ParametricVaR(HOLDINGS, CONFIDENCE)]

    # Daily forecasts (Phase 2) side by side, plus the actual P&L each day.
    var = pd.concat([rolling_var(m, returns, WINDOW) for m in models], axis=1)
    var["actual_pnl"] = pnl.reindex(var.index)

    # Rupee P&L of each asset each day: return x rupees held.
    # e.g. Infosys -21% on Rs 10 lakh = -Rs 2.1 lakh.
    asset_pnl = returns * pd.Series(HOLDINGS)[returns.columns]

    # Stressed window, chosen by historical VaR exactly as in Phase 3.
    stress = find_stress_window(var["historical"], returns, WINDOW)
    svar = stressed_var(models, stress["returns"])

    summary, log_rows = {}, []
    for m in models:
        b = find_breaches(var[m.name], var["actual_pnl"])       # Phase 4
        var[f"breach_{m.name}"] = b
        k = kupiec_pof(int(b.sum()), len(b), 1 - CONFIDENCE)
        zone = rolling_zone(b, 250).iloc[-1]                     # today's zone
        summary[m.name] = {
            "next_day_var": m.predict(returns.iloc[-WINDOW:]),
            "stressed_var": svar[m.name],
            "breaches": int(b.sum()),
            "expected": (1 - CONFIDENCE) * len(b),
            "breach_rate": b.mean(),
            "kupiec_LR": k["LR"],
            "kupiec_p": k["p_value"],
            "kupiec": k["verdict"],
            "breaches_250d": int(zone["breaches_250d"]),
            "zone": zone["zone"],
        }
        # One log row per breach day.
        for d in b.index[b]:
            day = asset_pnl.loc[d]                 # each asset's P&L that day
            driver = day.idxmin()                  # asset with the biggest loss
            loss = -var.loc[d, "actual_pnl"]       # loss as a positive number
            log_rows.append({
                "date": d.date(),
                "model": m.name,
                "var": var.loc[d, m.name],
                "actual_pnl": var.loc[d, "actual_pnl"],
                "excess": loss - var.loc[d, m.name],          # how far beyond VaR
                "excess_pct": loss / var.loc[d, m.name] - 1,  # e.g. 0.42 = 42% beyond
                "driver": driver,
                "driver_pnl": day[driver],
                **{f"pnl_{a}": day[a] for a in day.index},     # every asset's P&L
            })

    breach_log = pd.DataFrame(log_rows).sort_values(["date", "model"], ascending=[False, True])
    return {"var": var, "asset_pnl": asset_pnl, "models": summary,
            "breach_log": breach_log, "stress": stress}


# ---------------------------------------------------------------------------
# PART 2 — small formatting helpers
# ---------------------------------------------------------------------------
def style_header_row(ws, row):
    """Make every filled cell in one row look like a header (blue, white, bold)."""
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal="center", wrap_text=True)


def set_widths(ws, widths):
    """Set column widths, e.g. {1: 14, 2: 30} -> column A = 14, B = 30 characters."""
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


# ---------------------------------------------------------------------------
# PART 3 — the sheets
# ---------------------------------------------------------------------------
def write_summary(ws, res):
    """Sheet 1: the page a manager reads first."""
    var = res["var"]
    last = var.index[-1]                                     # latest data day
    pnl_today = var.loc[last, "actual_pnl"]

    ws["A1"] = "VaR Breach Report: 1-day 99% VaR, Rs 60 lakh Indian multi-asset portfolio"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (f"Data to {last.date()} | forecasts from {var.index[0].date()} "
                f"({len(var):,} days) | window {WINDOW} days | constant Rs 10 lakh per asset")

    # --- Latest day ------------------------------------------------------
    ws["A4"] = "Latest day (VaR forecast made the previous trading day vs what happened)"
    ws["A4"].font = Font(bold=True, size=12)
    ws.append(["Date", "Model", "VaR forecast for this day", "Actual P&L", "Breach?"])
    style_header_row(ws, ws.max_row)
    for name in res["models"]:
        breached = bool(var.loc[last, f"breach_{name}"])
        ws.append([last.date(), name, var.loc[last, name], pnl_today,
                   "YES" if breached else "no"])
        ws.cell(ws.max_row, 3).number_format = RUPEE
        ws.cell(ws.max_row, 4).number_format = RUPEE
        if breached:                                          # highlight a breach in red
            ws.cell(ws.max_row, 5).fill = PatternFill("solid", fgColor=ZONE_FILL["red"])

    # --- Model validation table -----------------------------------------
    ws.append([])
    ws.append(["Model validation"])
    ws.cell(ws.max_row, 1).font = Font(bold=True, size=12)
    headers = ["Model", "VaR for next trading day", "Stressed VaR", "Breaches", "Expected (1%)",
               "Breach rate", "Kupiec LR", "Kupiec p-value", "Kupiec (5%)",
               "Breaches, last 250d", "Basel zone"]
    ws.append(headers)
    style_header_row(ws, ws.max_row)
    for name, s in res["models"].items():
        ws.append([name, s["next_day_var"], s["stressed_var"], s["breaches"],
                   round(s["expected"], 1), s["breach_rate"], round(s["kupiec_LR"], 2),
                   s["kupiec_p"], s["kupiec"], s["breaches_250d"], s["zone"].upper()])
        r = ws.max_row
        ws.cell(r, 2).number_format = RUPEE
        ws.cell(r, 3).number_format = RUPEE
        ws.cell(r, 6).number_format = "0.00%"
        ws.cell(r, 8).number_format = "0.00E+00"              # scientific, e.g. 5.30E-06
        ws.cell(r, 11).fill = PatternFill("solid", fgColor=ZONE_FILL[s["zone"]])

    st = res["stress"]
    ws.append([])
    ws.append([f"Stressed window (highest historical VaR): {st['start'].date()} -> "
               f"{st['end'].date()}"])
    ws.append(["Basel zones: green 0-4, amber 5-9, red 10+ breaches in 250 days. "
               "Kupiec rejects if p < 0.05."])
    set_widths(ws, {1: 14, 2: 15, 3: 15, 4: 14, 5: 13, 6: 12, 7: 11, 8: 14, 9: 12,
                    10: 14, 11: 12})


def write_breach_log(ws, res):
    """Sheet 2: every breach, newest first, with the asset that drove the loss."""
    log = res["breach_log"]
    assets = [c for c in log.columns if c.startswith("pnl_")]
    headers = (["Date", "Model", "VaR forecast", "Actual P&L", "Loss beyond VaR",
                "Beyond VaR (%)", "Driver asset", "Driver P&L"]
               + [a.removeprefix("pnl_") for a in assets])
    ws.append(headers)
    style_header_row(ws, 1)
    for _, r in log.iterrows():
        ws.append([r["date"], r["model"], r["var"], r["actual_pnl"], r["excess"],
                   r["excess_pct"], r["driver"], r["driver_pnl"]] + [r[a] for a in assets])
    # Rupee format for all money columns, % for the percentage column.
    money_cols = [3, 4, 5, 8] + list(range(9, 9 + len(assets)))
    for row in ws.iter_rows(min_row=2):
        for c in money_cols:
            row[c - 1].number_format = RUPEE
        row[5].number_format = "0%"
    ws.freeze_panes = "A2"                         # header stays visible when scrolling
    ws.auto_filter.ref = ws.dimensions             # filter arrows on every column
    set_widths(ws, {i: 14 for i in range(1, len(headers) + 1)} | {7: 13})


def write_chart_data(ws, res):
    """Sheet 4: date, actual P&L, -VaR per model, and P&L on breach days only."""
    var = res["var"]
    names = list(res["models"])
    ws.append(["Date", "Actual P&L"] + [f"-VaR {n}" for n in names] + ["Breach (historical)"])
    style_header_row(ws, 1)
    for d, r in var.iterrows():
        # VaR is plotted as a NEGATIVE line so it sits on the loss side with the P&L.
        breach_point = r["actual_pnl"] if r["breach_historical"] else None
        ws.append([d.date(), r["actual_pnl"]] + [-r[n] for n in names] + [breach_point])
    set_widths(ws, {1: 12, 2: 14, 3: 16, 4: 16, 5: 18})
    return ws.max_row          # last data row, used by the charts


def add_line_chart(ws_chart, ws_data, first_row, last_row, title, anchor):
    """
    Native Excel line chart of P&L vs -VaR between two rows of the data sheet.
    Breach days are shown as red dots (a series with markers and no line).
    """
    chart = LineChart()
    chart.title = title
    chart.y_axis.title = "Rupees"
    chart.y_axis.number_format = '"₹"#,##0'
    chart.height, chart.width = 9, 26                         # size in cm
    # Reference = a block of cells on the data sheet.
    # Columns 2-5 hold: P&L, -VaR historical, -VaR parametric, breach points.
    values = Reference(ws_data, min_col=2, max_col=5, min_row=first_row, max_row=last_row)
    dates = Reference(ws_data, min_col=1, min_row=first_row, max_row=last_row)
    chart.add_data(values, titles_from_data=False)   # one line ("series") per column
    # Name each line for the legend (the header row isn't inside a 250-day slice).
    for s, name in zip(chart.series, SERIES_NAMES, strict=True):
        s.tx = SeriesLabel(v=name)
    chart.set_categories(dates)                      # dates along the x-axis
    chart.x_axis.number_format = "mmm-yy"
    # Style: thin lines; breach series = red dots only.
    for s in chart.series[:3]:
        s.smooth = False
        s.graphicalProperties.line.width = 12700            # 1 point (units: EMU)
    breach = chart.series[3]
    breach.marker.symbol = "circle"
    breach.marker.size = 6
    breach.marker.graphicalProperties.solidFill = "C00000"
    breach.graphicalProperties.line.noFill = True          # no line, only dots
    ws_chart.add_chart(chart, anchor)


# ---------------------------------------------------------------------------
# PART 4 — put it together
# ---------------------------------------------------------------------------
def main():
    res = build_results()
    wb = Workbook()
    ws_summary = wb.active                     # a new workbook starts with one sheet
    ws_summary.title = "Summary"
    write_summary(ws_summary, res)
    write_breach_log(wb.create_sheet("Breach Log"), res)
    ws_chart = wb.create_sheet("Charts")
    ws_data = wb.create_sheet("Chart Data")
    last_row = write_chart_data(ws_data, res)

    add_line_chart(ws_chart, ws_data, max(2, last_row - 249), last_row,
                   "Last 250 days: actual P&L vs -VaR (red dots = historical VaR breaches)",
                   "A1")
    add_line_chart(ws_chart, ws_data, 2, last_row,
                   "Full history: actual P&L vs -VaR", "A20")

    last_date = res["var"].index[-1].date()
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"var_breach_report_{last_date}.xlsx"
    wb.save(path)

    # Short console summary.
    print(f"Report: {path}")
    for name, s in res["models"].items():
        print(f"  {name:11s} next-day VaR Rs {s['next_day_var'] / 1e5:.2f} L | "
              f"SVaR Rs {s['stressed_var'] / 1e5:.2f} L | {s['breaches']} breaches | "
              f"Kupiec {s['kupiec']} | zone {s['zone']}")
    print(f"  breach log rows: {len(res['breach_log'])}")


if __name__ == "__main__":
    main()
