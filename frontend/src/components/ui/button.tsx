import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "../../lib/utils";

type ButtonVariant = "default" | "secondary" | "outline";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variantClass: Record<ButtonVariant, string> = {
  default: "bw-btn-default",
  secondary: "bw-btn-secondary",
  outline: "bw-btn-outline",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "default", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      className={cn(
        "bw-btn",
        variantClass[variant],
        className
      )}
      {...props}
    />
  );
});
