import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppProvider } from "./lib/context";
import { AuthProvider, useAuth } from "./lib/auth";
import { Home } from "./screens/Home";
import { Upload } from "./screens/Upload";
import { MyReports } from "./screens/MyReports";
import { SearchScreen } from "./screens/SearchScreen";
import { Comparison } from "./screens/Comparison";
import { Favorites } from "./screens/Favorites";
import { Settings } from "./screens/Settings";
import { Login } from "./screens/Login";
import { ReportDetail } from "./report/ReportDetail";
import "./index.css";

const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/upload", element: <Upload /> },
  { path: "/reports", element: <MyReports /> },
  { path: "/reports/:id", element: <ReportDetail /> },
  { path: "/search", element: <SearchScreen /> },
  { path: "/compare", element: <Comparison /> },
  { path: "/favorites", element: <Favorites /> },
  { path: "/settings", element: <Settings /> },
]);

// Auth gate: unauthenticated users see the login screen; the whole app is
// behind sign-in so no document data is ever fetched without a user.
function Gate() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="center" style={{ minHeight: "100vh" }}><div className="spinner" /></div>;
  if (!user) return <Login />;
  return <RouterProvider router={router} />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProvider>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </AppProvider>
  </React.StrictMode>
);
