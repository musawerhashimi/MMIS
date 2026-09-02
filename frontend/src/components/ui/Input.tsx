import { forwardRef } from 'react'
import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const FIELD =
  'w-full rounded-lg border bg-[var(--surface)] px-3 text-sm outline-none transition-colors ' +
  'placeholder:text-[var(--text-subtle)] focus:border-brand-500 disabled:opacity-60'

interface FieldProps {
  label?: string
  error?: string
  hint?: string
  required?: boolean
}

function Wrapper({
  label,
  error,
  hint,
  required,
  htmlFor,
  children,
}: FieldProps & { htmlFor?: string; children: React.ReactNode }) {
  return (
    <div>
      {label && (
        <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-medium">
          {label}
          {required && <span className="ml-0.5 text-red-500">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <p className="mt-1 text-[11px] text-red-600 dark:text-red-400">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-[11px] text-subtle">{hint}</p>
      ) : null}
    </div>
  )
}

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & FieldProps
>(function Input({ label, error, hint, required, className, id, ...rest }, ref) {
  return (
    <Wrapper label={label} error={error} hint={hint} required={required} htmlFor={id}>
      <input
        ref={ref}
        id={id}
        className={cn(FIELD, 'h-9.5', error && 'border-red-400', className)}
        {...rest}
      />
    </Wrapper>
  )
})

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement> & FieldProps
>(function Textarea({ label, error, hint, required, className, id, rows = 4, ...rest }, ref) {
  return (
    <Wrapper label={label} error={error} hint={hint} required={required} htmlFor={id}>
      <textarea
        ref={ref}
        id={id}
        rows={rows}
        className={cn(FIELD, 'py-2 leading-relaxed', error && 'border-red-400', className)}
        {...rest}
      />
    </Wrapper>
  )
})

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement> & FieldProps
>(function Select({ label, error, hint, required, className, id, children, ...rest }, ref) {
  return (
    <Wrapper label={label} error={error} hint={hint} required={required} htmlFor={id}>
      <select
        ref={ref}
        id={id}
        className={cn(FIELD, 'h-9.5 pr-8', error && 'border-red-400', className)}
        {...rest}
      >
        {children}
      </select>
    </Wrapper>
  )
})
