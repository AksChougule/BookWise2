import { HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function ScrollArea({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("bw-scroll-area", className)} {...props} />;
}
