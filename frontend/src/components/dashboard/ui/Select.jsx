import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from "../../../lib/utils";

const Select = React.forwardRef(({ className, variant = "default", size = "default", ...props }, ref) => {
  const variants = {
    default: "bg-background border-input text-foreground focus:ring-ring",
    outline: "bg-transparent border-input text-foreground focus:ring-ring",
    ghost: "bg-transparent border-transparent text-foreground focus:ring-ring hover:bg-accent",
  }

  const sizes = {
    default: "h-10 px-4 py-2",
    sm: "h-9 px-3 text-sm",
    lg: "h-11 px-4 text-base",
  }

  return (
    <div className="relative inline-flex">
      <select
        className={cn(
          "appearance-none w-full rounded-md border font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
          "disabled:pointer-events-none disabled:opacity-50",
          "pr-10",
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
    </div>
  )
})
Select.displayName = "Select"

export { Select }
