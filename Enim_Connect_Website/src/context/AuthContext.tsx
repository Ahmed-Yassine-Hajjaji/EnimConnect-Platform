import React, { createContext, useContext, useState, useCallback } from "react";
import { api } from "../api/client";

interface AuthContextValue {
  isAuthenticated: boolean;
  role: string | null;
  mustChangePassword: boolean;
  login: (email: string, password: string) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, role: string) => Promise<void>;
  clearMustChangePassword: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(api.isAuthenticated());
  const [role, setRole] = useState<string | null>(api.getRole());
  const [mustChangePassword, setMustChangePassword] = useState(api.mustChangePassword());

  const login = useCallback(async (email: string, password: string) => {
    await api.login(email, password);
    setIsAuthenticated(true);
    setRole(api.getRole());
    setMustChangePassword(api.mustChangePassword());
  }, []);

  const googleLogin = useCallback(async (credential: string) => {
    await api.googleLogin(credential);
    setIsAuthenticated(true);
    setRole(api.getRole());
    setMustChangePassword(false);
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setIsAuthenticated(false);
    setRole(null);
    setMustChangePassword(false);
  }, []);

  const register = useCallback(
    async (email: string, password: string, role: string) => {
      await api.register(email, password, role);
    },
    []
  );

  const clearMustChangePassword = useCallback(() => {
    setMustChangePassword(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, mustChangePassword, login, googleLogin, logout, register, clearMustChangePassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
