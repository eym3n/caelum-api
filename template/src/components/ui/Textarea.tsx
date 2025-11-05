import * as React from "react";
import { twMerge } from "tailwind-merge";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={twMerge(
        "input-base min-h-24 w-full rounded-lg px-3 py-2",
        className
      )}
      {...props}
    />
  );
});
Textarea.displayName = "Textarea";
