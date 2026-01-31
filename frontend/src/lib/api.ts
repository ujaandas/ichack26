import type { OSMAddress, PolygonCoords } from "./types";

function getCentroid(coords: PolygonCoords) {
    const lon = coords.reduce((sum, c) => sum + c.longitude, 0) / coords.length;
    const lat = coords.reduce((sum, c) => sum + c.latitude, 0) / coords.length;
    return { lat, lon };
}

function getBestName(address: OSMAddress) {
    return (
        address.country ||
        address.ocean ||
        address.sea ||
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
    return getBestName(data.address || {});
}

export async function sendPolygonToBackend(coords: PolygonCoords) {
    if (!coords || coords.length < 3) {
        throw new Error("Polygon must have at least 3 vertices.");
    }

    // ensure closed
    const closed = coords[0];
    const last = coords[coords.length - 1];
    const isClosed = closed.latitude === last.latitude && closed.longitude === last.longitude;

    const polygon = isClosed ? coords : [...coords, closed];

    // geojson?
    const geojson = {
        type: "Feature",
        geometry: {
            type: "Polygon",
            coordinates: [
                polygon.map(p => [p.longitude, p.latitude])
            ]
        },
        properties: {}
    };

    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    if (!backendUrl) {
        throw new Error("Missing VITE_BACKEND_URL environment variable.");
    }

    const res = await fetch(`${backendUrl}/polygon`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(geojson)
    });

    if (!res.ok) {
        throw new Error(`Backend error: ${res.status}`);
    }

    return res.json();
}