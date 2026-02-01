import {
  Cartesian2,
  Cartesian3,
  Cartographic,
  Ion,
  ScreenSpaceEventType,
} from "cesium";
import { useRef, useState } from "react";
import {
  CameraFlyTo,
  ScreenSpaceEvent,
  ScreenSpaceEventHandler,
  type CesiumComponentRef,
} from "resium";
import { Viewer as ResiumViewer } from "resium";
import { Viewer as CesiumViewer } from "cesium";
import { Math as CesiumMath } from "cesium";
import { SidebarActive } from "@/components/sidebar-active";
import { SidebarInactive } from "@/components/sidebar-inactive";
import type { BackendResponse, DrawingState, PolygonCoords } from "@/lib/types";
import { fetchAreaName, sendPolygonToBackend } from "@/lib/api";
import ResiumPolygonDraw from "./components/resium-polygon-draw";
import { AlertDialogDemo } from "./components/intro-alert";
import DrawButton from "./components/draw-button";

Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ACCESS_TOKEN;

export default function App() {
  const viewerRef = useRef<CesiumComponentRef<CesiumViewer>>(null);
  const mouseDownPos = useRef<Cartesian2 | null>(null);
  const [currentPolygonVertices, setCurrentPolygonVertices] =
    useState<PolygonCoords>([]);
  const isDragging = useRef(false);
  // const [isDrawing, setIsDrawing] = useState<boolean>(false);
  // const [isReadyToClear, setIsReadyToClear] = useState(false);
  // const [hasCompletedPolygon, setHasCompletedPolygon] = useState<boolean>(false);
  const [drawingState, setDrawingState] = useState<DrawingState>({
    isDrawing: false,
    isClearable: false,
    isCompleted: false,
  });
  const [areaName, setAreaName] = useState("");
  const [backendResponse, setBackendResponse] = useState<BackendResponse>();

  const dragThreshold = 5; // pixels

  const handleStartDrawPolygon = () => {
    // X is available, clear all
    if (drawingState?.isClearable) {
      console.log("X is available, clear all");
      setCurrentPolygonVertices([]);
      setDrawingState({
        isDrawing: false,
        isClearable: false,
        isCompleted: false,
      });
      return;
    }

    // Drawing mode, confirm/clear based on # vertices
    if (drawingState?.isDrawing) {
      // Can we finish the polygon?
      if (currentPolygonVertices.length > 2) {
        console.log("is drawing, >2 vertices");
        // Get final polygon
        const finalPolygon = [
          ...currentPolygonVertices,
          currentPolygonVertices[0],
        ] as PolygonCoords;

        (async () => {
          try {
            setDrawingState((prev) => ({ ...prev, isClearable: true }));
            const name = await fetchAreaName(finalPolygon);
            setAreaName(name);
            setCurrentPolygonVertices(finalPolygon);
            const resp = await sendPolygonToBackend(finalPolygon);
            setBackendResponse(resp);
            setDrawingState({
              isDrawing: true,
              isClearable: true,
              isCompleted: true,
            });
          } catch (err) {
            console.error(err);
          }
        })();
      } else {
        console.log("is drawing, but <2 vertices");
        setDrawingState({
          isClearable: false,
          isDrawing: false,
          isCompleted: false,
        });
        setCurrentPolygonVertices([]);
      }

      return;
    }

    // CASE 3: User clicks pencil -> start drawing
    if (!drawingState.isDrawing) {
      console.log("drawing!");
      setCurrentPolygonVertices([]);
      setDrawingState((prev) => ({
        ...prev,
        isDrawing: true,
        isCompleted: false,
      }));
    }
  };

  const handleAddPolygonVertex = (point: Cartographic) => {
    console.log(`Added vertex at ${point}`);
    setCurrentPolygonVertices(
      (prev) => [...prev, point] as unknown as PolygonCoords,
    );
  };

  const handleMapLeftClick = (e: { position: Cartesian2 }) => {
    if (!drawingState.isDrawing) return;

    if (!viewerRef.current?.cesiumElement) return;

    const scene = viewerRef.current?.cesiumElement.scene;
    const camera = viewerRef.current?.cesiumElement.camera;

    const ray = camera.getPickRay(e.position);

    if (!ray) return;

    const cartesian = scene.globe.pick(ray, scene);

    if (!cartesian) return;

    const carto = Cartographic.fromCartesian(cartesian);
    const point = new Cartographic(
      CesiumMath.toDegrees(carto.longitude),
      CesiumMath.toDegrees(carto.latitude),
    );
    handleAddPolygonVertex(point);
  };

  return (
    <main className="flex flex-row h-screen font-Satoshi">
      <AlertDialogDemo />

      {/* Sidebar */}
      {drawingState.isCompleted ? (
        <SidebarActive area={areaName} data={backendResponse} />
      ) : (
        <SidebarInactive />
      )}

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
              if (!drawingState.isDrawing) return;

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

      <DrawButton
        drawingState={drawingState}
        vertexCount={currentPolygonVertices.length}
        startDrawingPolygon={handleStartDrawPolygon}
      // startDrawingRectangle={handleStartDrawRectangle}
      />
    </main>
  );
}
