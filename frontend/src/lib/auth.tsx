import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "../api/client";
import type { User } from "../types";

interface AuthCtx {
  user: User | null;
  ready: boolean; // finished restoring session
  isGuest: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  guest: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>(null as unknown as AuthCtx);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const logout = () => {
    // Tell the server so a guest workspace is wiped; then clear local state.
    api.logout().catch(() => {});
    setToken(null);
    setUser(null);
  };

  // A 401 from any request clears the session.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null);
      setUser(null);
    });
  }, []);

  // Restore session on load if a token is present.
  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
  };
  const register = async (email: string, password: string) => {
    const res = await api.register(email, password);
    setToken(res.access_token);
    setUser(res.user);
  };
  // Guest token goes to sessionStorage (ephemeral) via setToken(..., true).
  const guest = async () => {
    const res = await api.guest();
    setToken(res.access_token, true);
    setUser(res.user);
  };

  return (
    <AuthContext.Provider value={{ user, ready, isGuest: !!user?.is_guest, login, register, guest, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
