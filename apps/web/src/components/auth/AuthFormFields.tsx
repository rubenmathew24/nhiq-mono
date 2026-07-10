"use client";

interface AuthFormFieldsProps {
  email: string;
  password: string;
  fullName?: string;
  showFullName?: boolean;
  onEmailChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onFullNameChange?: (v: string) => void;
  error?: string;
  disabled?: boolean;
}

const inputClass =
  "w-full rounded-xl border border-border bg-card px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 transition-shadow";

export default function AuthFormFields({
  email,
  password,
  fullName = "",
  showFullName = false,
  onEmailChange,
  onPasswordChange,
  onFullNameChange,
  error,
  disabled = false,
}: AuthFormFieldsProps) {
  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {showFullName && (
        <div className="space-y-1.5">
          <label htmlFor="fullName" className="text-sm font-medium text-foreground">
            Full name
          </label>
          <input
            id="fullName"
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(e) => onFullNameChange?.(e.target.value)}
            placeholder="Jane Smith"
            className={inputClass}
            disabled={disabled}
            required
          />
        </div>
      )}

      <div className="space-y-1.5">
        <label htmlFor="email" className="text-sm font-medium text-foreground">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
          placeholder="you@example.com"
          className={inputClass}
          disabled={disabled}
          required
        />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="password" className="text-sm font-medium text-foreground">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
          placeholder="••••••••"
          className={inputClass}
          disabled={disabled}
          required
          minLength={8}
        />
      </div>
    </div>
  );
}
