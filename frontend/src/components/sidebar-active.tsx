import { TrendingUp } from "lucide-react";
import { EmptySidebar } from "./sidebar-empty";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { ScrollArea } from "./ui/scroll-area";
import { Separator } from "./ui/separator";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "./ui/chart";
import { Area, AreaChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, XAxis } from "recharts";
import { Badge } from "./ui/badge";

const landUseData = [
    { name: "Residential", value: 35, color: "#3b82f6" },
    { name: "Commercial", value: 25, color: "#8b5cf6" },
    { name: "Green Space", value: 20, color: "#22c55e" },
    { name: "Industrial", value: 12, color: "#f59e0b" },
    { name: "Water", value: 8, color: "#06b6d4" },
];

const populationTrend = [
    { year: "2019", population: 12400 },
    { year: "2020", population: 12800 },
    { year: "2021", population: 13200 },
    { year: "2022", population: 14100 },
    { year: "2023", population: 15200 },
    { year: "2024", population: 16800 },
];

const environmentalData = [
    { month: "Jan", airQuality: 72, greenIndex: 45 },
    { month: "Feb", airQuality: 68, greenIndex: 42 },
    { month: "Mar", airQuality: 75, greenIndex: 52 },
    { month: "Apr", airQuality: 82, greenIndex: 65 },
    { month: "May", airQuality: 78, greenIndex: 78 },
    { month: "Jun", airQuality: 65, greenIndex: 82 },
];

const chartConfig: ChartConfig = {
    population: {
        label: "Population",
        color: "#3b82f6",
    },
    airQuality: {
        label: "Air Quality",
        color: "#22c55e",
    },
    greenIndex: {
        label: "Green Index",
        color: "#10b981",
    },
};

interface SidebarActiveProps {
    area: string
}

export function SidebarActive({ area }: SidebarActiveProps) {
    return (
        <ScrollArea className="h-full">
            <EmptySidebar title={area} subtitle="(Approximated based on polygon center)">
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
                                <Badge variant="default" className="bg-amber-500 hover:bg-amber-600">Grade B</Badge>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">Avg. Soil Loss Rate</span>
                                <span className="font-medium">8.4 tons/ha/yr</span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">High Risk Areas</span>
                                <span className="font-medium text-orange-600">22%</span>
                            </div>
                        </div>

                        <Separator />

                        <div>
                            <h4 className="text-xs font-semibold mb-3">RUSLE Factor Analysis</h4>
                            <div className="space-y-2.5">
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">R - Rainfall Erosivity</span>
                                        <span className="font-medium">245 MJ·mm/ha·h</span>
                                    </div>
                                    <Progress value={65} className="h-1.5" />
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">K - Soil Erodibility</span>
                                        <span className="font-medium">0.32 t·ha·h/MJ·mm</span>
                                    </div>
                                    <Progress value={40} className="h-1.5" />
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">LS - Slope Length/Steepness</span>
                                        <span className="font-medium">1.0 (assumed)</span>
                                    </div>
                                    <Progress value={56} className="h-1.5" />
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">C - Cover Management</span>
                                        <span className="font-medium">0.15 (good)</span>
                                    </div>
                                    <Progress value={85} className="h-1.5" />
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">P - Support Practice</span>
                                        <span className="font-medium">0.8 (adequate)</span>
                                    </div>
                                    <Progress value={75} className="h-1.5" />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Environmental Metrics */}
                <Card className="mb-4">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Environmental Metrics</CardTitle>
                        <CardDescription className="text-xs">Air quality & vegetation index</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ChartContainer config={chartConfig} className="h-[120px] w-full">
                            <LineChart data={environmentalData}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                                <XAxis
                                    dataKey="month"
                                    tickLine={false}
                                    axisLine={false}
                                    fontSize={10}
                                    tick={{ fill: "hsl(var(--muted-foreground))" }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="airQuality"
                                    stroke="#22c55e"
                                    strokeWidth={2}
                                    dot={false}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="greenIndex"
                                    stroke="#10b981"
                                    strokeWidth={2}
                                    dot={false}
                                    strokeDasharray="4 4"
                                />
                                <ChartTooltip content={<ChartTooltipContent />} />
                            </LineChart>
                        </ChartContainer>
                    </CardContent>
                </Card>

                {/* Land Use Distribution */}
                <Card className="mb-4">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Land Use Distribution</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[140px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={landUseData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={35}
                                        outerRadius={55}
                                        paddingAngle={2}
                                        dataKey="value"
                                    >
                                        {landUseData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-3">
                            {landUseData.map((item) => (
                                <div key={item.name} className="flex items-center gap-2 text-xs">
                                    <div
                                        className="size-2.5 rounded-full"
                                        style={{ backgroundColor: item.color }}
                                    />
                                    <span className="text-muted-foreground">{item.name}</span>
                                    <span className="font-medium ml-auto">{item.value}%</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Population Trend */}
                <Card className="mb-4">
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">Population Trend</CardTitle>
                            <Badge variant="secondary" className="text-xs font-normal">
                                <TrendingUp className="size-3 mr-1 text-emerald-500" />
                                +10.5%
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <ChartContainer config={chartConfig} className="h-[120px] w-full">
                            <AreaChart data={populationTrend}>
                                <defs>
                                    <linearGradient id="populationGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                                        <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis
                                    dataKey="year"
                                    tickLine={false}
                                    axisLine={false}
                                    fontSize={10}
                                    tick={{ fill: "hsl(var(--muted-foreground))" }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="population"
                                    stroke="#3b82f6"
                                    strokeWidth={2}
                                    fill="url(#populationGradient)"
                                />
                                <ChartTooltip content={<ChartTooltipContent />} />
                            </AreaChart>
                        </ChartContainer>
                    </CardContent>
                </Card>
            </EmptySidebar>
        </ScrollArea>
    )
}
