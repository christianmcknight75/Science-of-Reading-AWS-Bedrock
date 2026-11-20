/** A real radio group (arrow keys work) with big labels. State is also shown by a thicker border. */
export function RadioChips<T extends string>({
  legend,
  name,
  options,
  value,
  onChange,
  hideLegend = false,
}: {
  legend: string;
  name: string;
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (v: T) => void;
  hideLegend?: boolean;
}) {
  return (
    <fieldset>
      <legend className={hideLegend ? "sr-only" : "mb-2 font-semibold"}>{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label
            key={o.value}
            className={`flex min-h-target cursor-pointer items-center gap-2 rounded-lg border px-4 font-semibold ${
              value === o.value ? "border-2 border-primary bg-bg" : "border-control bg-surface"
            }`}
          >
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
              className="h-5 w-5 accent-[var(--color-primary)]"
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
