import { Cartesian2, Cartesian3, Cartographic, Color, Ion, ScreenSpaceEventType } from "cesium";
import { useRef, useState } from "react";
import { CameraFlyTo, Entity, PointGraphics, PolygonGraphics, PolylineGraphics, ScreenSpaceEvent, ScreenSpaceEventHandler, type CesiumComponentRef } from "resium";
import { Viewer as ResiumViewer, } from "resium"
import { Viewer as CesiumViewer } from "cesium";
import { Math as CesiumMath } from "cesium";
import { Button } from "./components/ui/button";
import { Check, Pencil } from "lucide-react";
import { SidebarActive } from "./components/sidebar-active";
import { SidebarInactive } from "./components/sidebar-inactive";


Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ACCESS_TOKEN;

type PolygonCoords = Cartographic[]

interface OSMAddress {
  country?: string
  ocean?: string
  sea?: string
}

export default function App() {
  const viewerRef = useRef<CesiumComponentRef<CesiumViewer>>(null);
  const mouseDownPos = useRef<Cartesian2 | null>(null);
  const isDragging = useRef(false);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [currentPolygonVertices, setCurrentPolygonVertices] = useState<PolygonCoords>([]);
  const [hasCompletedPolygon, setHasCompletedPolygon] = useState<boolean>(false);
  const [areaName, setAreaName] = useState("");

  const dragThreshold = 5; // pixels


  function getBestName(address: OSMAddress) {
    return (
      address.country ||
      address.ocean ||
      address.sea ||
      "???"
    );
  }

  function getCentroid(coords: PolygonCoords) {
    const lon = coords.reduce((sum, c) => sum + c.longitude, 0) / coords.length;
    const lat = coords.reduce((sum, c) => sum + c.latitude, 0) / coords.length;
    return { lat, lon };
  }

  async function fetchAreaName(coords: PolygonCoords) {
    const { lat, lon } = getCentroid(coords);

    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10&addressdetails=1`;

    const res = await fetch(url, {
      headers: { "User-Agent": "ICHack26/1.0" }
    });

    const data = await res.json();

    console.log(data.address)
    return getBestName(data.address || {});
  }

  const handleStartDrawClick = () => {
    console.log("Clicked 'draw polygon' button.");

    // Clear only when "start" is clicked AND existing polygon
    if (!isDrawing && currentPolygonVertices.length > 1) {
      setCurrentPolygonVertices([]);
      setHasCompletedPolygon(false);
    }

    if (isDrawing) {
      if (currentPolygonVertices.length > 2) {
        const finalPolygon = [
          ...currentPolygonVertices,
          currentPolygonVertices[0],
        ] as PolygonCoords;


        fetchAreaName(finalPolygon).then(name => {
          setAreaName(name);
          setCurrentPolygonVertices(finalPolygon);
          setHasCompletedPolygon(true);
        });
      }
    }


    setIsDrawing(!isDrawing);

    if (currentPolygonVertices.length > 0) {
      console.log(
        `Completed vertex: ${JSON.stringify(currentPolygonVertices)}`
      );
    }
  };

  const handleAddPolygonVertex = (point: Cartographic) => {
    console.log(`Added vertex at ${point}`)
    setCurrentPolygonVertices(prev =>
      [...prev, point] as unknown as PolygonCoords
    );
  };

  const handleMapLeftClick = (e: { position: Cartesian2 }) => {
    if (!isDrawing) return;

    if (!viewerRef.current?.cesiumElement) return;

    const scene = viewerRef.current?.cesiumElement.scene;
    const camera = viewerRef.current?.cesiumElement.camera;

    const ray = camera.getPickRay(e.position);

    if (!ray) return;

    const cartesian = scene.globe.pick(ray, scene);

    if (!cartesian) return;

    const carto = Cartographic.fromCartesian(cartesian);
    carto.longitude = CesiumMath.toDegrees(carto.longitude);
    carto.latitude = CesiumMath.toDegrees(carto.latitude);

    handleAddPolygonVertex(carto);
  };

  const toCartesianArray = (coords: PolygonCoords) => {
    return coords.map(c =>
      Cartesian3.fromDegrees(c.longitude, c.latitude, c.height)
    );
  };

  return (
    <main className="flex flex-row h-screen">

      {/* Sidebar */}
      {
        hasCompletedPolygon ?
          (
            <SidebarActive area={`Somewhere Around ${areaName}`} />
          ) :
          (
            <SidebarInactive />
          )
      }

      {/* Cesium viewer */}
      <ResiumViewer
        className="w-full h-full"
        ref={viewerRef}
        animation={false}
        selectionIndicator={false}
        infoBox={false}
        homeButton={false}
        sceneModePicker={false}
        projectionPicker={false}
        baseLayerPicker={false}
        navigationHelpButton={false}
        timeline={false}
        fullscreenButton={false}
        vrButton={false}
      >
        <CameraFlyTo
          once={true}
          destination={Cartesian3.fromDegrees(-0.1276, 51.5072, 50000.0)}
        />

        <ScreenSpaceEventHandler>
          <ScreenSpaceEvent
            type={ScreenSpaceEventType.LEFT_DOWN}
            action={(e) => {
              const pos = (e as { position: Cartesian2 }).position;
              mouseDownPos.current = Cartesian2.clone(pos);
              isDragging.current = false;
            }}
          />

          <ScreenSpaceEvent
            type={ScreenSpaceEventType.MOUSE_MOVE}
            action={(e) => {
              if (!mouseDownPos.current) return;

              const pos = (e as { endPosition: Cartesian2 }).endPosition;
              const dx = pos.x - mouseDownPos.current.x;
              const dy = pos.y - mouseDownPos.current.y;

              if (Math.sqrt(dx * dx + dy * dy) > dragThreshold) {
                isDragging.current = true;
              }
            }}
          />

          <ScreenSpaceEvent
            type={ScreenSpaceEventType.LEFT_UP}
            action={(e) => {
              if (!isDrawing) return;

              if (!isDragging.current) {
                handleMapLeftClick(e as { position: Cartesian2 });
              }

              mouseDownPos.current = null;
              isDragging.current = false;
            }}
          />
        </ScreenSpaceEventHandler>

        {/* Polygon vertices */}
        {currentPolygonVertices.map((v, i) => (
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

        {/* Polygon lines */}
        {currentPolygonVertices.length >= 2 && (
          <Entity>
            <PolylineGraphics
              positions={toCartesianArray(currentPolygonVertices)}
              width={3}
              material={Color.CYAN}
            />
          </Entity>
        )}

        {/* Polygon fill */}
        {currentPolygonVertices.length >= 3 && (
          <Entity>
            <PolygonGraphics
              hierarchy={toCartesianArray(currentPolygonVertices)}
              material={Color.RED.withAlpha(0.4)}
            />
          </Entity>
        )}
      </ResiumViewer>

      <Button
        onClick={handleStartDrawClick}
        size="icon-lg"
        className={`absolute bottom-6 right-6 size-14 rounded-full shadow-lg transition-al ${isDrawing
          ? "bg-emerald-500 hover:bg-emerald-600"
          : "bg-white hover:bg-primary/90"
          }`}
      >
        {isDrawing ? (
          <Check className="size-6" color="white" />
        ) : (
          <Pencil className="size-6" />
        )}
        <span className="sr-only">
          {isDrawing ? "Finish drawing" : "Start drawing"}
        </span>
      </Button>
    </main>
  );
}
