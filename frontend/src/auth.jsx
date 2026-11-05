import React, { createContext, useContext, useEffect, useState } from "react";
import { api, getToken } from "./api.js";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!getToken());

  useEffect(() => {
    if (getToken()) {
      api.get("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
    }
    const onExpired = () => setUser(null);
    window.addEventListener("auth-expired", onExpired);
    return () => window.removeEventListener("auth-expired", onExpired);
  }, []);

  const finish = (data) => {
    localStorage.setItem("token", data.token);
    setUser(data.user);
  };
  const login = async (email, password) => finish(await api.post("/auth/login", { email, password }));
  const register = async (name, email, password) => finish(await api.post("/auth/register", { name, email, password }));
  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return <Ctx.Provider value={{ user, setUser, loading, login, register, logout }}>{children}</Ctx.Provider>;
}
