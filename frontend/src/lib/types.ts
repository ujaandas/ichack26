import type { Cartographic } from "cesium"

export type PolygonCoords = Cartographic[]
export interface OSMAddress {
    country?: string
    ocean?: string
    sea?: string
}
export interface DrawingState {
    isDrawing: boolean
    isClearable: boolean
    isCompleted: boolean
}

export interface BackendResponse {
    success: boolean;
    computation_time_sec: number;
    timestamp: string;

    polygon: {
        type: "Feature";
        geometry: {
            type: "Polygon";
            coordinates: number[][][];
        };
        properties: {
            centroid: [number, number];
            bbox: [number, number, number, number];
            area_hectares: number;
        };
    };

    polygon_metadata: {
        area_km2: number;
        centroid: [number, number];
        bbox: [number, number, number, number];
        num_vertices: number;
    };

    erosion: {
        mean: number;
        max: number;
        min: number;
        stddev: number;
        p50: number;
        p95: number;
        total_soil_loss_tonnes: number;
    };

    factors: Record<
        "R" | "K" | "LS" | "C" | "P",
        {
            mean: number;
            stddev: number;
            min: number;
            max: number;
            unit: string;
            contribution_pct: number;
            source: string;
        }
    >;

    highlights: Highlight[];
    num_hotspots: number;

    validation: {
        high_veg_reduction_pct: number;
        flat_terrain_reduction_pct: number;
        bare_soil_increase_pct: number;
        model_valid: boolean;
        notes: string;
    };

    crop_yield: {
        yield_t_ha: number;
        crop_name: string;
        location: [number, number];
        week: number;
        coverage: string;
        error: string | null;
    };

    carbon_sequestration: {
        carbon_rate_mg_ha_yr: number;
        location: [number, number];
        climate: {
            annual_mean_temp_c: number;
            annual_mean_precip_mm: number;
        };
        soil: {
            classification: string;
        };
        coverage: string;
        error: string | null;
    };

    tile_urls: string[] | null;
}

export interface Highlight {
    id: string;
    geometry: {
        type: "Polygon";
        coordinates: number[][][];
    };
    properties: {
        area_ha: number;
        mean_erosion: number;
        max_erosion: number;
        dominant_factor: string;
    };
    reason: string;
    severity: string;
}
