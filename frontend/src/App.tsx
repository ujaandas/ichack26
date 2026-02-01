import { Cartesian2, Cartesian3, Cartographic, Ion, ScreenSpaceEventType } from "cesium";
import { useRef, useState } from "react";
import { CameraFlyTo, ScreenSpaceEvent, ScreenSpaceEventHandler, type CesiumComponentRef } from "resium";
import { Viewer as ResiumViewer, } from "resium"
import { Viewer as CesiumViewer } from "cesium";
import { Math as CesiumMath } from "cesium";
import { SidebarActive } from "@/components/sidebar-active";
import { SidebarInactive } from "@/components/sidebar-inactive";
import type { PolygonCoords } from "@/lib/types";
import { fetchAreaName, sendPolygonToBackend } from "@/lib/api";
import DrawPolygonButton from "@/components/draw-polygon-button";
import ResiumPolygonDraw from "./components/resium-polygon-draw";
import { AlertDialogDemo } from "./components/intro-alert";

Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ACCESS_TOKEN;

export default function App() {
  const viewerRef = useRef<CesiumComponentRef<CesiumViewer>>(null);
  const mouseDownPos = useRef<Cartesian2 | null>(null);
  const isDragging = useRef(false);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [isReadyToClear, setIsReadyToClear] = useState(false);
  const [currentPolygonVertices, setCurrentPolygonVertices] = useState<PolygonCoords>([]);
  const [hasCompletedPolygon, setHasCompletedPolygon] = useState<boolean>(false);
  const [areaName, setAreaName] = useState("");

  const dragThreshold = 5; // pixels

  const handleStartDrawClick = () => {
    console.log("Clicked polygon button.");

    // CASE 1: User clicks X → clear polygon
    if (isReadyToClear) {
      setCurrentPolygonVertices([]);
      setHasCompletedPolygon(false);
      setIsReadyToClear(false);
      setIsDrawing(false);
      return;
    }

    // CASE 2: User clicks check → finish polygon
    if (isDrawing) {
      if (currentPolygonVertices.length > 2) {
        const finalPolygon = [
          ...currentPolygonVertices,
          currentPolygonVertices[0],
        ] as PolygonCoords;

        fetchAreaName(finalPolygon).then(name => {
          setIsReadyToClear(true); // show X button
          setAreaName(name);
          setCurrentPolygonVertices(finalPolygon);
          setHasCompletedPolygon(true);
          setIsDrawing(false);

          console.log(finalPolygon)

          sendPolygonToBackend(finalPolygon)
            .then(resp => console.log("Saved polygon:", resp))
            .catch(err => console.error("Backend error:", err));
        });
      } else {
        setIsDrawing(false);
        setIsReadyToClear(false);
        setHasCompletedPolygon(false);
      }

      return;
    }

    // CASE 3: User clicks pencil → start drawing
    if (!isDrawing) {
      setCurrentPolygonVertices([]);
      setHasCompletedPolygon(false);
      setIsDrawing(true);
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

  return (
    <main className="flex flex-row h-screen font-Satoshi">

      <AlertDialogDemo />

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

        <ResiumPolygonDraw vertices={currentPolygonVertices} />

      </ResiumViewer>

      <DrawPolygonButton
        isDrawing={isDrawing}
        isReadyToClear={isReadyToClear}
        vertexCount={currentPolygonVertices.length}
        clickHandler={handleStartDrawClick}
      />

    </main>
  );
}
