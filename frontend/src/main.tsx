import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppProvider } from "./lib/context";
import { Home } from "./screens/Home";
import { Upload } from "./screens/Upload";
import { MyReports } from "./screens/MyReports";
import { SearchScreen } from "./screens/SearchScreen";
import { Comparison } from "./screens/Comparison";
import { Favorites } from "./screens/Favorites";
import { Settings } from "./screens/Settings";
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

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  </React.StrictMode>
);
