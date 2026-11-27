import type { ComponentProps } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn/ui Button pattern, with Tokoflux variants.
const buttonVariants = cva("inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50", {
  variants: { variant: { primary: "bg-[var(--lime)] text-[var(--lime-ink)] hover:brightness-95", outline: "border border-[var(--line)] hover:bg-[var(--surface-raised)]" } },
  defaultVariants: { variant: "primary" },
});

export function Button({ className, variant, asChild, ...props }: ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return <Component className={twMerge(clsx(buttonVariants({ variant }), className))} {...props} />;
}
