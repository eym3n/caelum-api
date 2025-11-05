"use client";
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";

const buttonVariants = cva(
  "btn-base rounded-lg focus-visible:outline-none",
  {
    variants: {
      variant: {
        primary:
          "bg-[color:var(--brand-500)] text-white hover:bg-[color:var(--brand-600)] active:bg-[color:var(--brand-700)] hover:shadow-xl transition-all duration-300 ease-[cubic-bezier(.2,.6,.2,1)] hover:scale-[1.025] active:scale-95",
        secondary:
          "bg-white text-[color:var(--color-foreground)] border border-[color:var(--color-border)] hover:bg-[color:var(--neutral-50)] transition-all duration-200",
        subtle:
          "bg-[color:var(--brand-50)] text-[color:var(--brand-700)] hover:bg-[color:var(--brand-100)] transition-colors",
        ghost:
          "bg-transparent text-[color:var(--color-foreground)] hover:bg-[color:var(--neutral-100)]",
        danger:
          "bg-[color:var(--danger-500)] text-white hover:opacity-90",
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-11 px-5 text-base",
      },
      full: { true: "w-full", false: "" },
    },
    defaultVariants: { variant: "primary", size: "md", full: false },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, full, ...props }, ref) => {
    return (
      <button ref={ref} className={twMerge(buttonVariants({ variant, size, full }), className)} {...props} />
    );
  }
);
Button.displayName = "Button";
