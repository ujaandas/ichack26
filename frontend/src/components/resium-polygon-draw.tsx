import type { PolygonCoords } from "@/lib/types"
import { Cartesian3, Color, PolygonHierarchy } from "cesium"
import { Entity, PointGraphics, PolygonGraphics, PolylineGraphics } from "resium"

interface ResiumPolygonDrawProps {
    vertices: PolygonCoords
}

export default function ResiumPolygonDraw({ vertices }: ResiumPolygonDrawProps) {
    return (
        <>
            {vertices.map((v, i) => (
                <Entity
                    key={i}
                    position={Cartesian3.fromDegrees(v.longitude, v.latitude)}
                >
                    <PointGraphics
                        pixelSize={10}
                        color={Color.YELLOW}
                        outlineColor={Color.BLACK}
                        outlineWidth={2}
                    />
                </Entity>
            ))}

            {vertices.length >= 2 && (
                <Entity>
                    <PolylineGraphics
                        positions={toCartesianArray(vertices)}
                        width={3}
                        material={Color.CYAN}
                    />
                </Entity>
            )}

            {vertices.length >= 3 && (
                <Entity>
                    <PolygonGraphics
                        hierarchy={new PolygonHierarchy(toCartesianArray(vertices))}
                        material={Color.RED.withAlpha(0.4)}
                    />
                </Entity>
            )}
        </>
    )
}

const toCartesianArray = (coords: PolygonCoords) => {
    return coords.map(c =>
        Cartesian3.fromDegrees(c.longitude, c.latitude, c.height)
    );
};
