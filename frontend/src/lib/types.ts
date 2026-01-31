import type { Cartographic } from "cesium"

export type PolygonCoords = Cartographic[]
export interface OSMAddress {
    country?: string
    ocean?: string
    sea?: string
}