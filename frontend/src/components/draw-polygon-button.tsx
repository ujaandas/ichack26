import { Check, Pencil, X } from "lucide-react"
import { Button } from "./ui/button"

interface DrawPolygonButtonProps {
    isDrawing: boolean
    isReadyToClear: boolean
    vertexCount: number
    clickHandler: () => void
}

export default function DrawPolygonButton({ isDrawing, isReadyToClear, vertexCount, clickHandler }: DrawPolygonButtonProps) {
    return (
        <Button
            onClick={clickHandler}
            size="icon-lg"
            className={`absolute bottom-6 right-6 size-14 rounded-full shadow-lg transition-colors
                ${isDrawing
                    ? vertexCount > 2
                        ? "bg-emerald-500 hover:bg-emerald-600" // can finish
                        : "bg-red-500 hover:bg-red-600"         // cannot finish
                    : isReadyToClear
                        ? "bg-red-500 hover:bg-red-600"
                        : "bg-white hover:bg-gray-200"
                }
                    `}
        >

            {isDrawing ? (
                vertexCount > 2
                    ? <Check className="size-6" color="white" />
                    : <X className="size-6" color="white" />
            ) : isReadyToClear ? (
                <X className="size-6" color="white" />
            ) : (
                <Pencil className="size-6" color="black" />
            )}


            <span className="sr-only">
                {isDrawing ? "Finish drawing" :
                    isReadyToClear ? "Clear drawing" :
                        "Start drawing"}
            </span>
        </Button>
    );
}
