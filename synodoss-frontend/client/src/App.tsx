import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Dashboard from "./pages/Dashboard";
import ScanDetail from "./pages/ScanDetail";
import DebateWorkspace from "./pages/DebateWorkspace";
import GraphExplorer from "./pages/GraphExplorer";
import { FloatingNav } from "./components/FloatingNav";
import { MouseSpotlight } from "./components/MouseSpotlight";
import { CommandPalette } from "./components/CommandPalette";

function Router() {
  return (
    <>
      <FloatingNav />
      <main className="pt-24">
        <Switch>
          <Route path={"/"} component={Dashboard} />
          <Route path={"/scans/:id/graph"} component={GraphExplorer} />
          <Route path={"/scans/:id"} component={ScanDetail} />
          <Route path={"/debates/:id"} component={DebateWorkspace} />
          <Route path={"/404"} component={NotFound} />
          {/* Final fallback route */}
          <Route component={NotFound} />
        </Switch>
      </main>
    </>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        switchable
      >
        <TooltipProvider>
          <Toaster />
          <MouseSpotlight />
          <CommandPalette />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
