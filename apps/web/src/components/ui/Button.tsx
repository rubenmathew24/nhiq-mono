import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "accent" | "ghost";

interface ButtonProps extends React.ComponentPropsWithoutRef<"button"> {
  variant?: ButtonVariant;
  href?: string;
  className?: string;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:opacity-90",
  accent:
    "bg-accent text-accent-foreground hover:opacity-90",
  ghost:
    "bg-transparent text-foreground hover:bg-muted",
};

export default function Button({
  variant = "primary",
  href,
  className,
  children,
  ...props
}: ButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-opacity",
    variantStyles[variant],
    className,
  );

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button type="button" className={classes} {...props}>
      {children}
    </button>
  );
}

export function ButtonWithArrow({
  variant = "primary",
  href,
  className,
  children,
  ...props
}: ButtonProps) {
  if (href) {
    return (
      <Button variant={variant} href={href} className={className}>
        {children}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    );
  }

  return (
    <Button variant={variant} className={className} {...props}>
      {children}
      <ArrowRight className="h-4 w-4" aria-hidden="true" />
    </Button>
  );
}
