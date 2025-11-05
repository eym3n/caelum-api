import * as React from "react";
import { twMerge } from "tailwind-merge";

export function Label({ className = "", ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={twMerge("block text-sm font-medium text-[--color-foreground]", className)} {...props} />;
}
