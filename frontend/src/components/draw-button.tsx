import type { DrawingState } from "@/lib/types";
import { Button } from "./ui/button";
import { Check, Pencil, X } from "lucide-react";

interface DrawButtonProps {
    drawingState: DrawingState
    vertexCount: number
    startDrawingPolygon: () => void
    // startDrawingRectangle: () => void
}

const getButtonColor = (drawingState: DrawingState, vertexCount: number) => {
    if (drawingState.isClearable) return "bg-red-500 hover:bg-red-600";
    if (drawingState.isDrawing && vertexCount > 2) return "bg-emerald-500 hover:bg-emerald-600";
    if (drawingState.isDrawing) return "bg-red-500 hover:bg-red-600";
    return "bg-white hover:bg-gray-200";
};

const getButtonSymbol = (color: string) => {
    if (color.startsWith("bg-red")) {
        return <X className="size-6" color="white" />;
    }

    if (color.startsWith("bg-emerald")) {
        return <Check className="size-6" color="white" />;
    }

    // white fallback
    return <Pencil className="size-6" color="black" />;
};


export default function DrawButton(
    { drawingState, vertexCount, startDrawingPolygon, }: DrawButtonProps) {

    const color = getButtonColor(drawingState, vertexCount);

    return (
        <Button onClick={startDrawingPolygon} size="icon-lg"
            className={`absolute bottom-6 right-6 size-14 rounded-full shadow-lg transition-colors ${color}`}>
            {getButtonSymbol(color)}
        </Button>
    );
}