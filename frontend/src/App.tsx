import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Layout from "@/components/Layout";
import CommandCenter from "@/pages/CommandCenter";
import RiskEvents from "@/pages/RiskEvents";
import RiskDetail from "@/pages/RiskDetail";
import Escalations from "@/pages/Escalations";
import RecoveryPnL from "@/pages/RecoveryPnL";
import Outbox from "@/pages/Outbox";
import AuditLedger from "@/pages/AuditLedger";
import Login from "@/pages/Login";
import { isAuthed } from "@/lib/auth";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <CommandCenter /> },
      { path: "risk", element: <RiskEvents /> },
      { path: "risk/:id", element: <RiskDetail /> },
      { path: "escalations", element: <Escalations /> },
      { path: "pnl", element: <RecoveryPnL /> },
      { path: "outbox", element: <Outbox /> },
      { path: "audit", element: <AuditLedger /> },
    ],
  },
]);

export default function App() {
  const [authed, setAuthed] = useState(isAuthed());
  if (!authed) return <Login onSuccess={() => setAuthed(true)} />;
  return <RouterProvider router={router} />;
}
