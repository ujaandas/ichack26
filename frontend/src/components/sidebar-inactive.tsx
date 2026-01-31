import { BarChart3, Layers, MapPin, MousePointer2 } from "lucide-react";
import { EmptySidebar } from "./sidebar-empty";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

export function SidebarInactive() {
    return (
        <EmptySidebar title="Getting Started" subtitle="kachow" >
            <>
                <Card className="mb-6 border-dashed">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <MousePointer2 className="size-4 text-muted-foreground" />
                            How to Use
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 text-sm text-muted-foreground">
                        <div className="flex gap-3">
                            <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                                1
                            </div>
                            <p>Click the pencil button in the bottom right corner to start drawing</p>
                        </div>
                        <div className="flex gap-3">
                            <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                                2
                            </div>
                            <p>Click on the map to place polygon vertices</p>
                        </div>
                        <div className="flex gap-3">
                            <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                                3
                            </div>
                            <p>Click the check button to complete your selection</p>
                        </div>
                    </CardContent>
                </Card>

                <div className="grid grid-cols-2 gap-3 mb-6">
                    <Card className="py-4">
                        <CardContent className="flex flex-col items-center justify-center p-0">
                            <MapPin className="size-5 text-muted-foreground mb-2" />
                            <p className="text-xs text-muted-foreground">Location</p>
                            <p className="text-sm font-medium text-foreground">London, UK</p>
                        </CardContent>
                    </Card>
                    <Card className="py-4">
                        <CardContent className="flex flex-col items-center justify-center p-0">
                            <Layers className="size-5 text-muted-foreground mb-2" />
                            <p className="text-xs text-muted-foreground">Vertices</p>
                            <p className="text-sm font-medium text-foreground">{67}</p>
                        </CardContent>
                    </Card>
                </div>

                <Card className="bg-muted/50 border-none">
                    <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                            <BarChart3 className="size-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="text-sm font-medium text-foreground">Ready to Analyze</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Complete a polygon selection to view detailed statistics, land use data, and environmental metrics for the area.
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </>
        </EmptySidebar>
    )
}