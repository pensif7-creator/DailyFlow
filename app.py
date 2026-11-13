from __future__ import annotations

import calendar
import math
from datetime import date, datetime
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def _safe_date(value: Any, fallback: date | None = None) -> date:
    """Parse ISO date values without allowing bad input to break the API."""
    fallback = fallback or date.today()
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return fallback


def _safe_amount(value: Any) -> float:
    try:
        amount = float(value)
        return amount if amount > 0 and math.isfinite(amount) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _minutes(start: Any, end: Any) -> int:
    """Return the duration of a same-day task in minutes."""
    try:
        start_time = datetime.strptime(str(start), "%H:%M")
        end_time = datetime.strptime(str(end), "%H:%M")
        duration = int((end_time - start_time).total_seconds() // 60)
        return max(0, min(duration, 24 * 60))
    except (TypeError, ValueError):
        return 0


def build_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """Build personalized schedule and money summaries from browser data.

    The API is stateless: submitted records are processed for this response only
    and are not written to a server database.
    """
    tasks = payload.get("tasks") if isinstance(payload.get("tasks"), list) else []
    expenses = payload.get("expenses") if isinstance(payload.get("expenses"), list) else []
    selected_day = _safe_date(payload.get("selected_date"))
    selected_month = str(payload.get("selected_month") or selected_day.strftime("%Y-%m"))
    if len(selected_month) != 7 or selected_month[4] != "-":
        selected_month = selected_day.strftime("%Y-%m")
    budget = _safe_amount(payload.get("budget"))

    day_tasks = [t for t in tasks if isinstance(t, dict) and str(t.get("date", "")) == selected_day.isoformat()]
    completed = [t for t in day_tasks if t.get("status") == "completed"]
    skipped = [t for t in day_tasks if t.get("status") == "skipped"]
    pending = [t for t in day_tasks if t.get("status", "planned") == "planned"]
    planned_minutes = sum(_minutes(t.get("start"), t.get("end")) for t in day_tasks)
    completed_minutes = sum(_minutes(t.get("start"), t.get("end")) for t in completed)
    completion_rate = (len(completed) / len(day_tasks) * 100) if day_tasks else 0.0
    duration_rate = (completed_minutes / planned_minutes * 100) if planned_minutes else 0.0
    productivity_score = round(0.7 * completion_rate + 0.3 * duration_rate) if day_tasks else 0

    if not day_tasks:
        productivity_label = "Belum ada data"
        productivity_tip = "Tambahkan beberapa kegiatan hari ini. Jadwal istirahat juga boleh dicatat sebagai kegiatan."
    elif productivity_score >= 80:
        productivity_label = "Produktif"
        productivity_tip = "Banyak rencana berhasil diselesaikan. Pertahankan ritme yang seimbang dan sisakan waktu istirahat."
    elif productivity_score >= 60:
        productivity_label = "Cukup konsisten"
        productivity_tip = "Sebagian rencana sudah berjalan. Pilih satu tugas penting untuk diselesaikan lebih dulu besok."
    else:
        productivity_label = "Perlu penyesuaian"
        productivity_tip = "Coba kurangi jumlah tugas, pecah tugas besar menjadi langkah kecil, dan beri jeda yang realistis."

    month_expenses = [
        e for e in expenses
        if isinstance(e, dict) and str(e.get("date", "")).startswith(selected_month)
    ]
    monthly_total = sum(_safe_amount(e.get("amount")) for e in month_expenses)
    remaining = budget - monthly_total
    category_totals: dict[str, float] = {}
    for expense in month_expenses:
        category = str(expense.get("category") or "Lainnya")[:40]
        category_totals[category] = category_totals.get(category, 0.0) + _safe_amount(expense.get("amount"))
    category_breakdown = [
        {"category": name, "amount": round(amount, 2)}
        for name, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ]

    try:
        month_year, month_number = map(int, selected_month.split("-"))
        days_in_month = calendar.monthrange(month_year, month_number)[1]
        if selected_month == date.today().strftime("%Y-%m"):
            days_elapsed = max(1, date.today().day)
        else:
            days_elapsed = days_in_month
    except (ValueError, TypeError):
        days_elapsed = 1
    average_per_day = monthly_total / days_elapsed

    if not month_expenses:
        money_tip = "Belum ada catatan pengeluaran pada bulan ini. Masukkan transaksi agar ringkasannya terbentuk."
    elif budget > 0 and monthly_total > budget:
        money_tip = "Pengeluaran sudah melewati anggaran. Tinjau kategori terbesar dan rencanakan batas yang realistis untuk sisa bulan ini."
    elif budget > 0 and remaining <= budget * 0.2:
        money_tip = "Sisa anggaran mulai menipis. Periksa kembali pengeluaran yang tidak terlalu penting."
    elif category_breakdown:
        money_tip = f"Kategori pengeluaran terbesar bulan ini adalah {category_breakdown[0]['category']}. Perhatikan apakah nilainya sesuai kebutuhan."
    else:
        money_tip = "Catat pengeluaran secara rutin agar pola keuangan terlihat lebih jelas."

    today_expenses = sum(
        _safe_amount(e.get("amount")) for e in expenses
        if isinstance(e, dict) and str(e.get("date", "")) == selected_day.isoformat()
    )

    return {
        "selected_date": selected_day.isoformat(),
        "selected_month": selected_month,
        "tasks": {
            "total": len(day_tasks),
            "completed": len(completed),
            "skipped": len(skipped),
            "pending": len(pending),
            "planned_minutes": planned_minutes,
            "completed_minutes": completed_minutes,
            "completion_rate": round(completion_rate),
            "duration_rate": round(duration_rate),
            "productivity_score": productivity_score,
            "productivity_label": productivity_label,
            "productivity_tip": productivity_tip,
        },
        "money": {
            "monthly_total": round(monthly_total, 2),
            "today_total": round(today_expenses, 2),
            "budget": round(budget, 2),
            "remaining": round(remaining, 2),
            "average_per_day": round(average_per_day, 2),
            "category_breakdown": category_breakdown,
            "money_tip": money_tip,
        },
    }


@app.get("/")
def index():
    return send_from_directory(app.root_path, "index.html")


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Data yang dikirim tidak valid."}), 400
    return jsonify(build_analysis(payload))


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
