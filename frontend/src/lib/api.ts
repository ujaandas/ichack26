import type { BackendResponse, OSMAddress, PolygonCoords } from "./types";

function getCentroid(coords: PolygonCoords) {
    const lon = coords.reduce((sum, c) => sum + c.longitude, 0) / coords.length;
    const lat = coords.reduce((sum, c) => sum + c.latitude, 0) / coords.length;
    return { lat, lon };
}

function getBestName(address: OSMAddress, isOcean: boolean) {
    // If it's ocean/sea, prioritize showing that instead of country
    if (isOcean) {
        return address.ocean || address.sea || "Ocean";
    }
    return (
        address.country ||
        "???"
    );
}

export async function fetchAreaName(coords: PolygonCoords) {
    const { lat, lon } = getCentroid(coords);

    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10&addressdetails=1`;

    const res = await fetch(url, {
        headers: { "User-Agent": "ICHack26/1.0" }
    });

    const data = await res.json();

    console.log(data.address);
    const address = data.address || {};
    // Check if it's ocean/sea - if these fields exist, it's a water body
    const isOcean = !!(address.ocean || address.sea);
    // Check if we have a valid country
    const hasCountry = !!address.country;
    return { name: getBestName(address, isOcean), isOcean, hasCountry };
}

export async function sendPolygonToBackend(coords: PolygonCoords): Promise<BackendResponse> {
    if (!coords || coords.length < 3) {
        throw new Error("Polygon must have at least 3 vertices.");
    }

    // ensure closed
    const closed = coords[0];
    const last = coords[coords.length - 1];
    const isClosed = closed.latitude === last.latitude && closed.longitude === last.longitude;

    const polygon = isClosed ? coords : [...coords, closed];

    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    if (!backendUrl) {
        throw new Error("Missing VITE_BACKEND_URL environment variable.");
    }

    console.log("Sending polygon to backend:", backendUrl + "/api/rusle");
    console.log("Coordinates count:", polygon.length);

    const res = await fetch(`${backendUrl}/api/rusle`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            coordinates: polygon.map(p => ({
                longitude: p.longitude,
                latitude: p.latitude
            })),
            options: {
                p_toggle: false,
                date_range: "2025-01-01/2025-12-31",
                threshold_t_ha_yr: 20.0,
                compute_sensitivities: true
            }
        })
    });

    console.log("Response status:", res.status);

    if (!res.ok) {
        const errorText = await res.text();
        console.error("Backend error response:", errorText);
        throw new Error(`Backend error: ${res.status} - ${errorText}`);
    }

    const data = await res.json();
    console.log("Backend data received:", data);
    return data;
}