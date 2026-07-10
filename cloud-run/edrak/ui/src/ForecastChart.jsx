// 12-month buffer chart: shortfall months in red, released obligations annotated.
import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { sar } from "./shared";

export default function ForecastChart({ forecast }) {
  const data = forecast.months.map((m) => ({
    name: `ش${m.month}`,
    buffer: m.buffer,
    // Range series for the uncertainty band (recharts draws [low, high] as an area).
    band: [m.buffer_low, m.buffer_high],
    ratio: m.obligation_ratio,
    events: m.events,
  }));
  const released = forecast.months.flatMap((m) =>
    m.events.map((e) => ({ month: m.month, ...e }))
  );
  const hasBand = forecast.months.some((m) => m.buffer_high !== m.buffer_low);

  return (
    <article className="simple-panel">
      <h2>الفائض الشهري المتوقع — 12 شهرًا عبر كل بنوكك</h2>
      <div className="chart-box" dir="ltr">
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="rgba(164,226,210,0.12)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#9fb5b0", fontSize: 12 }} />
            <YAxis yAxisId="buffer" tick={{ fill: "#9fb5b0", fontSize: 12 }} width={52} />
            <YAxis yAxisId="ratio" orientation="right" unit="%" tick={{ fill: "#7fa8d0", fontSize: 11 }} width={44} />
            <Tooltip
              contentStyle={{ background: "#0a1718", border: "1px solid rgba(164,226,210,0.3)", borderRadius: 8 }}
              labelStyle={{ color: "#d7ece7" }}
              formatter={(value, key) => {
                if (key === "ratio") return [`${value}%`, "نسبة الالتزامات"];
                if (key === "band") return [`${sar(value[0])} — ${sar(value[1])}`, "نطاق التقدير"];
                return [sar(value), "الفائض المتوقع"];
              }}
            />
            <ReferenceLine yAxisId="buffer" y={0} stroke="rgba(255,170,164,0.6)" />
            {hasBand && (
              <Area
                yAxisId="buffer"
                dataKey="band"
                stroke="none"
                fill="#75f0c8"
                fillOpacity={0.14}
                isAnimationActive={false}
              />
            )}
            <Bar yAxisId="buffer" dataKey="buffer" radius={[4, 4, 0, 0]} maxBarSize={26}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.buffer < 0 ? "#ff6f66" : "#75f0c8"} />
              ))}
            </Bar>
            <Line yAxisId="ratio" dataKey="ratio" stroke="#7fb2f0" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      {hasBand && (
        <p className="helper chart-note">
          المنطقة المظللة تمثّل نطاق عدم اليقين بناءً على تذبذب إنفاقك الشهري الفعلي.
        </p>
      )}
      {released.length > 0 && (
        <div className="event-chips">
          {released.map((e) => (
            <span className="event-chip" key={`${e.month}-${e.label}`}>
              الشهر {e.month}: ينتهي {e.label} ويتحرر {sar(e.amount)}
            </span>
          ))}
        </div>
      )}
      <div className="metrics">
        <span>نسبة الالتزامات الآن: {forecast.obligation_ratio_now}%</span>
        <span>ذروة النسبة: {forecast.obligation_ratio_peak}%</span>
        <span>النسبة بعد 12 شهرًا: {forecast.obligation_ratio_month_12}%</span>
        <span>تغطية المدخرات: {forecast.months_of_savings_cover} شهر</span>
        {forecast.first_shortfall_month && (
          <span className="warn-chip">
            أول عجز: الشهر {forecast.first_shortfall_month} بمقدار {sar(forecast.first_shortfall_amount)}
          </span>
        )}
        {forecast.salary_timing_variance && <span className="warn-chip">راتبك لا يصل في يوم ثابت</span>}
      </div>
    </article>
  );
}
