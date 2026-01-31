import { EmptySidebar } from "./sidebar-empty";

export function SidebarInactive() {
    return (
        <EmptySidebar title="No Area Selected"
            subtitle="Use the polygon tool on the bottom right to draw and select a shape."
        >
            <></>
        </EmptySidebar>
    )
}