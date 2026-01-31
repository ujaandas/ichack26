import type { ReactNode } from "react";

interface EmptySidebarProps {
    title: string
    subtitle: string
    className?: string
    children: ReactNode
}

export function EmptySidebar({ title, subtitle, className, children }: EmptySidebarProps) {
    return (
        <div className={`flex flex-col h-full p-6 max-w-md ${className}`}>
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-foreground">{title}</h1>
                <p className="text-muted-foreground mt-1">
                    {subtitle}
                </p>
            </div>

            {children}
        </div>
    )
}