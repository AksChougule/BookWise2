import { InputHTMLAttributes, forwardRef } from "react";

import { cn } from "../../lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref
) {
  return (
    <input
      ref={ref}
      className={cn(
        "bw-input",
        className
      )}
      {...props}
    />
  );
});
