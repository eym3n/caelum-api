import * as React from "react";
import { twMerge } from "tailwind-merge";

export function Section({ className = "", ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <section className={twMerge("section-y", className)} {...props} />
  );
}

export function SectionInner({ className = "", ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge("container-max layout-gutter", className)} {...props} />;
}
