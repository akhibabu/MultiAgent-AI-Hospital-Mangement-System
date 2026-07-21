import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';

const fieldClass =
  'w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 disabled:opacity-60';

const errorFieldClass =
  'w-full rounded-lg border border-red-400 bg-transparent px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-500/20';

interface FieldWrapProps {
  label: string;
  htmlFor: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}

export function FieldWrap({
  label,
  htmlFor,
  error,
  required,
  children,
}: FieldWrapProps) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
      >
        {label}
        {required ? <span className="text-red-500"> *</span> : null}
      </label>
      {children}
      {error ? <p className="mt-1 text-xs text-red-600">{error}</p> : null}
    </div>
  );
}

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function TextInput({ label, error, id, ...props }: TextInputProps) {
  const inputId = id || props.name || label;
  return (
    <FieldWrap label={label} htmlFor={inputId} error={error} required={props.required}>
      <input
        id={inputId}
        className={error ? errorFieldClass : fieldClass}
        {...props}
      />
    </FieldWrap>
  );
}

interface TextSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export function TextSelect({
  label,
  error,
  id,
  options,
  placeholder,
  ...props
}: TextSelectProps) {
  const inputId = id || props.name || label;
  return (
    <FieldWrap label={label} htmlFor={inputId} error={error} required={props.required}>
      <select
        id={inputId}
        className={error ? errorFieldClass : fieldClass}
        {...props}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FieldWrap>
  );
}

interface TextTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
}

export function TextTextarea({
  label,
  error,
  id,
  ...props
}: TextTextareaProps) {
  const inputId = id || props.name || label;
  return (
    <FieldWrap label={label} htmlFor={inputId} error={error} required={props.required}>
      <textarea
        id={inputId}
        className={`${error ? errorFieldClass : fieldClass} min-h-24`}
        {...props}
      />
    </FieldWrap>
  );
}
