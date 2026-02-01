import { EmptySidebar } from "./sidebar-empty";
import { MapPin, Mouse, Layers, Info } from "lucide-react";
import { Card } from "@/components/ui/card";

export function SidebarInactive() {
    return (
        <EmptySidebar title="Select an Area to Get Started"
            subtitle="Use the polygon tool on the bottom right to draw and select a shape."
        >
            <div className="space-y-4 pb-6">
                {/* Quick Start Guide */}
                <Card className="p-4 bg-white border-slate-200">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-blue-50 rounded-lg">
                            <Mouse className="h-5 w-5 text-blue-600" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-slate-900 text-base">Draw Your Selection</h3>
                            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                                Click the pencil and then points on the map to create a polygon. Press the green tick to complete your selection.
                            </p>
                        </div>
                    </div>
                </Card>

                {/* Feature Info */}
                <Card className="p-4 bg-white border-slate-200">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-emerald-50 rounded-lg">
                            <Layers className="h-5 w-5 text-emerald-600" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-slate-900 text-base">View Data Layers</h3>
                            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                                Once selected, explore multiple data layers including terrain, vegetation, and infrastructure.
                            </p>
                        </div>
                    </div>
                </Card>

                {/* Analysis Info */}
                <Card className="p-4 bg-white border-slate-200">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-purple-50 rounded-lg">
                            <MapPin className="h-5 w-5 text-purple-600" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-slate-900 text-base">Analyze Geospatial Data</h3>
                            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                                Access detailed statistics, visualizations, and insights for your selected area.
                            </p>
                        </div>
                    </div>
                </Card>

                {/* Tips */}
                <div className="mt-6 pt-6 border-t border-slate-200">
                    <div className="flex items-start gap-2">
                        <Info className="h-4 w-4 text-slate-500 mt-0.5 flex-shrink-0" />
                        <div>
                            <h4 className="font-medium text-slate-700 text-sm">Pro Tips</h4>
                            <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
                                <li className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span>Click and drag to span and orbit the globe</span>
                                </li>
                                <li className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span>Use the zoom controls to navigate large areas</span>
                                </li>
                                <li className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span>Export data in multiple formats (CSV, GeoJSON)</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </EmptySidebar>
    )
}
