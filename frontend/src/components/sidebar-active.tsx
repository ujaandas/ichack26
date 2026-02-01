import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { EmptySidebar } from "./sidebar-empty";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { ScrollArea } from "./ui/scroll-area";
import { Separator } from "./ui/separator";
import { Badge } from "./ui/badge";
import type { BackendResponse } from "@/lib/types";

interface SidebarActiveProps {
    data?: BackendResponse;
    area: string;
}

function getErosionGrade(meanErosion: number): { grade: string; variant: "default" | "secondary" | "destructive" | "outline" } {
    if (meanErosion < 5) return { grade: "Grade A", variant: "secondary" };
    if (meanErosion < 10) return { grade: "Grade B", variant: "default" };
    if (meanErosion < 20) return { grade: "Grade C", variant: "outline" };
    return { grade: "Grade D", variant: "destructive" };
}


export function SidebarActive({ data, area }: SidebarActiveProps) {
    if (!data) {
        return (
            <EmptySidebar
                title={area}
                subtitle="Something went wrong...">
                <></>
            </EmptySidebar>
        )
    }
    const erosionGrade = getErosionGrade(data.erosion.mean);
    const coordinates = data.polygon_metadata.centroid;

    console.log(`Coordinates hereeere: ${coordinates}`)

    return (
        <ScrollArea className="h-full">
            <EmptySidebar
                title={area}
                subtitle={`${coordinates[1].toFixed(4)}°N, ${coordinates[0].toFixed(4)}°E`}
            >
                {/* Area Information */}
                <Card className="mb-4">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Area Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Total Area</span>
                            <span className="font-medium">{data.polygon_metadata.area_km2.toFixed(2)} km²</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Area (Hectares)</span>
                            <span className="font-medium">{data.polygon.properties.area_hectares.toFixed(2)} ha</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">High Risk Hotspots</span>
                            <span className="font-medium text-orange-600">{data.num_hotspots}</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Soil Erosion Assessment */}
                <Card className="mb-4">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Soil Erosion Assessment (RUSLE)</CardTitle>
                        <CardDescription className="text-xs">Revised Universal Soil Loss Equation</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-muted-foreground">Overall Erosion Grade</span>
                                <Badge variant={erosionGrade.variant}>{erosionGrade.grade}</Badge>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Avg. Soil Loss Rate</span>
                                <span className="font-medium">{data.erosion.mean.toFixed(2)} t/ha/yr</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Max. Soil Loss Rate</span>
                                <span className="font-medium">{data.erosion.max.toFixed(2)} t/ha/yr</span>
                            </div>
                            {data.erosion.total_soil_loss_tonnes != null && (
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-muted-foreground">Total Soil Loss</span>
                                    <span className="font-medium text-orange-600">
                                        {data.erosion.total_soil_loss_tonnes.toFixed(0)} tonnes/yr
                                    </span>
                                </div>
                            )}
                        </div>

                        <Separator />

                        <div>
                            <h4 className="text-xs font-semibold mb-3">RUSLE Factor Analysis</h4>
                            <div className="space-y-2.5">
                                {/* R Factor */}
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">R - Rainfall Erosivity</span>
                                        <span className="font-medium">{data.factors.R.mean.toFixed(1)} {data.factors.R.unit}</span>
                                    </div>
                                    <Progress
                                        value={data.factors.R.contribution_pct ?? 0}
                                        className="h-1.5"
                                    />
                                    <p className="text-[10px] text-muted-foreground">
                                        Contribution: {data.factors.R.contribution_pct?.toFixed(1) ?? 'N/A'}%
                                    </p>
                                </div>

                                {/* K Factor */}
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">K - Soil Erodibility</span>
                                        <span className="font-medium">{data.factors.K.mean.toFixed(3)} {data.factors.K.unit}</span>
                                    </div>
                                    <Progress
                                        value={data.factors.K.contribution_pct ?? 0}
                                        className="h-1.5"
                                    />
                                    <p className="text-[10px] text-muted-foreground">
                                        Contribution: {data.factors.K.contribution_pct?.toFixed(1) ?? 'N/A'}%
                                    </p>
                                </div>

                                {/* LS Factor */}
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">LS - Slope Length/Steepness</span>
                                        <span className="font-medium">{data.factors.LS.mean.toFixed(2)} {data.factors.LS.unit}</span>
                                    </div>
                                    <Progress
                                        value={data.factors.LS.contribution_pct ?? 0}
                                        className="h-1.5"
                                    />
                                    <p className="text-[10px] text-muted-foreground">
                                        Contribution: {data.factors.LS.contribution_pct?.toFixed(1) ?? 'N/A'}%
                                    </p>
                                </div>

                                {/* C Factor */}
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">C - Cover Management</span>
                                        <span className="font-medium">{data.factors.C.mean.toFixed(3)} {data.factors.C.unit}</span>
                                    </div>
                                    <Progress
                                        value={data.factors.C.contribution_pct ?? 0}
                                        className="h-1.5"
                                    />
                                    <p className="text-[10px] text-muted-foreground">
                                        Contribution: {data.factors.C.contribution_pct?.toFixed(1) ?? 'N/A'}%
                                    </p>
                                </div>

                                {/* P Factor - Only shown when p_toggle is enabled */}
                                {data.factors.P && (
                                    <div className="space-y-1">
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="text-muted-foreground">P - Support Practice</span>
                                            <span className="font-medium">{data.factors.P.mean.toFixed(2)} {data.factors.P.unit}</span>
                                        </div>
                                        <Progress
                                            value={data.factors.P.contribution_pct ?? 0}
                                            className="h-1.5"
                                        />
                                        <p className="text-[10px] text-muted-foreground">
                                            Contribution: {data.factors.P.contribution_pct?.toFixed(1) ?? 'N/A'}%
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Model Validation */}
                <Card className="mb-4">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">Model Validation</CardTitle>
                            {data.validation.model_valid ? (
                                <Badge variant="secondary" className="text-xs">
                                    <CheckCircle2 className="size-3 mr-1 text-emerald-500" />
                                    Valid
                                </Badge>
                            ) : (
                                <Badge variant="destructive" className="text-xs">
                                    <AlertTriangle className="size-3 mr-1" />
                                    Issues
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">High Veg Reduction</span>
                            <span className="font-medium">{data.validation.high_veg_reduction_pct.toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Flat Terrain Reduction</span>
                            <span className="font-medium">{data.validation.flat_terrain_reduction_pct.toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Bare Soil Increase</span>
                            <span className="font-medium">{data.validation.bare_soil_increase_pct.toFixed(1)}%</span>
                        </div>
                        {data.validation.notes && (
                            <>
                                <Separator className="my-2" />
                                <p className="text-xs text-muted-foreground">{data.validation.notes}</p>
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* Crop Yield */}
                {data.crop_yield && !data.crop_yield.error && data.crop_yield.yield_t_ha != null && (
                    <Card className="mb-4">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Crop Yield Estimate</CardTitle>
                            <CardDescription className="text-xs">{data.crop_yield.crop_name}</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Estimated Yield</span>
                                <span className="font-medium">{data.crop_yield.yield_t_ha.toFixed(2)} t/ha</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Week</span>
                                <span className="font-medium">Week {data.crop_yield.week}</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Coverage</span>
                                <Badge variant="outline" className="text-xs">
                                    {data.crop_yield.coverage}
                                </Badge>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Carbon Sequestration */}
                {data.carbon_sequestration && !data.carbon_sequestration.error && data.carbon_sequestration.carbon_rate_mg_ha_yr != null && (
                    <Card className="mb-4">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm">Carbon Sequestration</CardTitle>
                            {data.carbon_sequestration.soil?.classification && (
                                <CardDescription className="text-xs">
                                    {data.carbon_sequestration.soil.classification}
                                </CardDescription>
                            )}
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Sequestration Rate</span>
                                <span className="font-medium">
                                    {data.carbon_sequestration.carbon_rate_mg_ha_yr.toFixed(2)} Mg/ha/yr
                                </span>
                            </div>
                            {data.carbon_sequestration.climate && (
                                <>
                                    <Separator className="my-2" />
                                    <div className="space-y-1.5">
                                        <h5 className="text-xs font-semibold">Climate Data</h5>
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="text-muted-foreground">Annual Mean Temp</span>
                                            <span className="font-medium">
                                                {data.carbon_sequestration.climate.annual_mean_temp_c.toFixed(1)}°C
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="text-muted-foreground">Annual Precipitation</span>
                                            <span className="font-medium">
                                                {data.carbon_sequestration.climate.annual_mean_precip_mm.toFixed(0)} mm
                                            </span>
                                        </div>
                                    </div>
                                </>
                            )}
                            <div className="flex items-center justify-between text-sm pt-1">
                                <span className="text-muted-foreground">Coverage</span>
                                <Badge variant="outline" className="text-xs">
                                    {data.carbon_sequestration.coverage}
                                </Badge>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Computation Info */}
                <Card className="mb-4">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Analysis Info</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Computation Time</span>
                            <span className="font-medium">{data.computation_time_sec.toFixed(2)}s</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Timestamp</span>
                            <span className="font-medium text-xs">{new Date(data.timestamp).toLocaleString()}</span>
                        </div>
                    </CardContent>
                </Card>
            </EmptySidebar>
        </ScrollArea>
    );
}