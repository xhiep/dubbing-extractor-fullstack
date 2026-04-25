/**
 * SliderField — label + range input đồng nhất theo Apple design system.
 *
 * Props:
 *   label       string   — tên hiển thị (không kèm giá trị)
 *   value       number
 *   displayValue string  — override hiển thị (nếu không truyền thì auto format từ value + unit)
 *   unit        string   — 'x' | 'px' | 's' | '' (mặc định '')
 *   min, max, step  number
 *   onChange    fn(number)
 *   disabled    bool
 */
const SliderField = ({
  label,
  value,
  displayValue,
  unit = '',
  min = 0,
  max = 100,
  step = 1,
  onChange,
  disabled = false,
}) => {
  const formatted = displayValue ?? `${value}${unit}`

  return (
    <div>
      <label className="block text-control font-medium text-apple-gray-secondary mb-3">
        {label}: <span className="text-apple-ink font-semibold">{formatted}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        disabled={disabled}
        className="w-full accent-apple-blue disabled:opacity-50"
      />
    </div>
  )
}

export default SliderField
