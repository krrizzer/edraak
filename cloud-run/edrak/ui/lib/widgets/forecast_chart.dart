import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../models.dart';
import '../theme.dart';
import 'widgets.dart';

/// The 12-month projection: a glowing gradient curve of the monthly buffer with
/// an honest uncertainty band, red shortfall markers, and release annotations.
class ForecastChart extends StatelessWidget {
  final Map<String, dynamic> forecast;
  const ForecastChart({super.key, required this.forecast});

  @override
  Widget build(BuildContext context) {
    final months = (forecast['months'] as List).cast<Map<String, dynamic>>();
    final buffer = [for (final m in months) (m['buffer'] as num).toDouble()];
    final low = [
      for (final m in months)
        ((m['buffer_low'] ?? m['buffer']) as num).toDouble()
    ];
    final high = [
      for (final m in months)
        ((m['buffer_high'] ?? m['buffer']) as num).toDouble()
    ];
    final maxAbs = [
      ...buffer.map((v) => v.abs()),
      ...high.map((v) => v.abs()),
      ...low.map((v) => v.abs())
    ].fold<double>(1, (a, b) => a > b ? a : b);
    final hasBand = [for (var i = 0; i < months.length; i++) high[i] != low[i]]
        .contains(true);

    final released = <String>[];
    for (final m in months) {
      for (final e in (m['events'] as List)) {
        released.add(
            'الشهر ${m['month']}: ينتهي ${e['label']} ويتحرر ${sar(e['amount'])}');
      }
    }

    return SectionCard(
      title: 'مسار الفائض الشهري — 12 شهرًا عبر كل بنوكك',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 220,
            child: LineChart(LineChartData(
              minY: -maxAbs * 1.15,
              maxY: maxAbs * 1.15,
              minX: 0,
              maxX: (months.length - 1).toDouble(),
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: maxAbs / 2,
                getDrawingHorizontalLine: (_) =>
                    const FlLine(color: Color(0x12A8D8E8), strokeWidth: 1),
              ),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                leftTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    interval: 1,
                    getTitlesWidget: (v, _) => Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text('ش${v.toInt() + 1}',
                          style: const TextStyle(
                              color: AppColors.textMuted, fontSize: 10.5)),
                    ),
                  ),
                ),
              ),
              extraLinesData: ExtraLinesData(horizontalLines: [
                HorizontalLine(
                  y: 0,
                  color: AppColors.danger.withValues(alpha: 0.55),
                  strokeWidth: 1.2,
                  dashArray: [6, 5],
                ),
              ]),
              lineTouchData: LineTouchData(
                touchTooltipData: LineTouchTooltipData(
                  getTooltipColor: (_) => AppColors.surfaceAlt,
                  getTooltipItems: (spots) => spots
                      .map((s) => s.barIndex == 0
                          ? LineTooltipItem(
                              'شهر ${s.x.toInt() + 1}\n${sar(s.y)}',
                              TextStyle(
                                  color: s.y < 0
                                      ? AppColors.danger
                                      : AppColors.primary,
                                  fontWeight: FontWeight.w800))
                          : null)
                      .toList(),
                ),
              ),
              betweenBarsData: hasBand
                  ? [
                      BetweenBarsData(
                          fromIndex: 1,
                          toIndex: 2,
                          color: AppColors.primary.withValues(alpha: 0.08))
                    ]
                  : [],
              lineBarsData: [
                // 0: the main buffer curve — gradient stroke, glow, red dots when negative.
                LineChartBarData(
                  spots: [
                    for (var i = 0; i < buffer.length; i++)
                      FlSpot(i.toDouble(), buffer[i])
                  ],
                  isCurved: true,
                  curveSmoothness: 0.32,
                  barWidth: 3.4,
                  gradient: const LinearGradient(
                      colors: [Color(0xFF2EE6A8), Color(0xFF4EA8FF)]),
                  shadow: Shadow(
                      color: AppColors.primary.withValues(alpha: 0.45),
                      blurRadius: 12),
                  dotData: FlDotData(
                    show: true,
                    getDotPainter: (spot, _, __, ___) => FlDotCirclePainter(
                      radius: spot.y < 0 ? 5 : 3,
                      color: spot.y < 0 ? AppColors.danger : AppColors.primary,
                      strokeWidth: spot.y < 0 ? 3 : 0,
                      strokeColor: AppColors.danger.withValues(alpha: 0.35),
                    ),
                  ),
                  belowBarData: BarAreaData(
                    show: true,
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        AppColors.primary.withValues(alpha: 0.16),
                        Colors.transparent
                      ],
                    ),
                  ),
                ),
                // 1 + 2: the uncertainty band edges (invisible lines, filled between).
                _bandLine(low),
                _bandLine(high),
              ],
            )),
          ),
          if (hasBand)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('المنطقة المظللة تعكس تذبذب إنفاقك الشهري الفعلي.',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
            ),
          const SizedBox(height: 12),
          for (final r in released)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Pill(r, color: AppColors.primary),
            ),
          const SizedBox(height: 6),
          Wrap(spacing: 8, runSpacing: 8, children: [
            Pill('الالتزامات الآن: ${forecast['obligation_ratio_now']}%',
                color: AppColors.accent),
            Pill('الذروة: ${forecast['obligation_ratio_peak']}%',
                color: AppColors.accent),
            Pill('تغطية المدخرات: ${forecast['months_of_savings_cover']} شهر',
                color: AppColors.accent),
            if (forecast['first_shortfall_month'] != null)
              Pill(
                  'أول عجز: الشهر ${forecast['first_shortfall_month']} (${sar(forecast['first_shortfall_amount'])})',
                  color: AppColors.danger),
          ]),
        ],
      ),
    );
  }

  LineChartBarData _bandLine(List<double> values) => LineChartBarData(
        spots: [
          for (var i = 0; i < values.length; i++)
            FlSpot(i.toDouble(), values[i])
        ],
        isCurved: true,
        curveSmoothness: 0.32,
        barWidth: 0,
        color: Colors.transparent,
        dotData: const FlDotData(show: false),
      );
}
