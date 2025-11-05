import * as React from "react";
import { Label } from "./Label";

interface FieldProps {
  label: string;
  hint?: string;
  children: React.ReactElement<{ id?: string }>;
}

export function Field({ label, hint, children }: FieldProps) {
  const id = React.useId();
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {React.cloneElement(children, { id })}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
