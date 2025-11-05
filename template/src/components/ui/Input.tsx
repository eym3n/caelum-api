import * as React from "react";
import { twMerge } from "tailwind-merge";

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "prefix"> {
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, prefix, suffix, ...props }, ref) => {
    return (
      <div className={twMerge("relative flex items-center", className)}>
        {prefix ? <span className="absolute left-3 text-muted-foreground text-sm">{prefix}</span> : null}
        <input
          ref={ref}
          className={twMerge(
            "input-base h-10 w-full rounded-lg px-3",
            prefix ? "pl-8" : "",
            suffix ? "pr-8" : ""
          )}
          {...props}
        />
        {suffix ? <span className="absolute right-3 text-muted-foreground text-sm">{suffix}</span> : null}
      </div>
    );
  }
);
Input.displayName = "Input";
