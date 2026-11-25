"""Regression tests for chart construction and bounded updates."""

from __future__ import annotations

from nexus.ui.widgets.charts import TimeSeriesChart


def test_chart_constructs_and_keeps_bounded_data(qtbot):
    chart = TimeSeriesChart([("CPU", "#ffffff")], max_points=3)
    qtbot.addWidget(chart)

    chart.append(1.0, {"CPU": 10.0})
    chart.append(2.0, {"CPU": None})
    chart.append(3.0, {"CPU": 30.0})
    chart.append(4.0, {"CPU": 40.0})

    assert list(chart._x) == [2.0, 3.0, 4.0]
    assert list(chart._buffers["CPU"]) == [None, 30.0, 40.0]
