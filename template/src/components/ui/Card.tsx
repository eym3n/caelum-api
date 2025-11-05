import * as React from "react";
import { twMerge } from "tailwind-merge";

export function Card({ className = "", ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge("card rounded-xl shadow-soft", className)} {...props} />;
}

export function CardHeader({ className = "", ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge("p-4 md:p-6 border-b border-[--color-border]", className)} {...props} />;
}

export function CardTitle({ className = "", ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={twMerge("text-base md:text-lg font-semibold", className)} {...props} />;
}

export function CardContent({ className = "", ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge("p-4 md:p-6", className)} {...props} />;
}

export function CardFooter({ className = "", ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge("p-4 md:p-6 border-t border-[--color-border]", className)} {...props} />;
}
