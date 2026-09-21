import { useState } from "react";
import { getToken } from "./api";
import { Jobs } from "./pages/Jobs";
import { Login } from "./pages/Login";

export default function App() {
  const [authed, setAuthed] = useState(() => Boolean(getToken()));

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  return <Jobs onLogout={() => setAuthed(false)} />;
}
