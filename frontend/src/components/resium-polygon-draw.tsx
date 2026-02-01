import type { PolygonCoords } from "@/lib/types"
import { Cartesian3, Color, PolygonHierarchy, PolylineGlowMaterialProperty } from "cesium"
import { Entity, PointGraphics, PolygonGraphics, PolylineGraphics } from "resium"
import { useMemo } from "react"

interface ResiumPolygonDrawProps {
    vertices: PolygonCoords
}

export default function ResiumPolygonDraw({ vertices }: ResiumPolygonDrawProps) {
    const cartesianVertices = useMemo(
        () => toCartesianArray(vertices),
        [vertices]
    )

    return (
        <>
            {/* Vertex points */}
            {vertices.map((v, i) => (
                <Entity
                    key={i}
                    position={Cartesian3.fromDegrees(v.longitude, v.latitude)}
                >
                    <PointGraphics
                        pixelSize={14}
                        color={Color.fromCssColorString("#ffd86b")}      // warm gold
                        outlineColor={Color.fromCssColorString("#2d2d2d")}
                        outlineWidth={3}
                    />
                </Entity>
            ))}

            {/* Polyline */}
            {vertices.length >= 2 && (
                <Entity>
                    <PolylineGraphics
                        positions={cartesianVertices}
                        width={4}
                        material={
                            new PolylineGlowMaterialProperty({
                                glowPower: 0.2,
                                color: Color.fromCssColorString("#00eaff").withAlpha(0.9)
                            })
                        }
                    />
                </Entity>
            )}

            {/* Polygon fill */}
            {vertices.length >= 3 && (
                <Entity>
                    <PolygonGraphics
                        hierarchy={new PolygonHierarchy(cartesianVertices)}
                        material={Color.fromCssColorString("#ff4f81").withAlpha(0.25)} // soft rose
                        outline={true}
                        outlineColor={Color.fromCssColorString("#ff4f81").withAlpha(0.8)}
                        outlineWidth={2}
                    />
                </Entity>
            )}
        </>
    )
}

const toCartesianArray = (coords: PolygonCoords) =>
    coords.map(c =>
        Cartesian3.fromDegrees(c.longitude, c.latitude, c.height)
    )
