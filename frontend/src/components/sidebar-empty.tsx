import type { ReactNode } from "react";
import logo from "@/../public/terraviz.png";

interface EmptySidebarProps {
    title: string;
    subtitle: string;
    className?: string;
    children: ReactNode;
}

export function EmptySidebar({ title, subtitle, className, children }: EmptySidebarProps) {
    return (
        <div className={`flex flex-col h-full bg-slate-50 border-r border-slate-200 max-w-md min-w-md ${className}`}>

            <div className="flex items-center gap-3 w-full h-20 px-5 bg-slate-100 text-slate-800">
                <img src={logo} className="h-12 w-12 object-contain drop-shadow" />
                <h1 className="text-3xl font-bold tracking-wide">TerraViz</h1>
            </div>

            <div className="p-6">
                <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
                <p className="text-lg text-slate-600 mt-1 leading-relaxed">
                    {subtitle}
                </p>
            </div>

            {/* Content */}
            <div className="px-6">
                {children}
            </div>
        </div>
    );
}
