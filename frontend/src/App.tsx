import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { useEffect, useRef } from 'react';
import { refreshToken } from './apis/authApi';
import { useAuthStore } from './store/authStore';


export default function App() {
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    const hasToken = Boolean(useAuthStore.getState().accessToken)
    if (!hasToken) refreshToken()
  }, [])

  return <RouterProvider router={router} />;
}
