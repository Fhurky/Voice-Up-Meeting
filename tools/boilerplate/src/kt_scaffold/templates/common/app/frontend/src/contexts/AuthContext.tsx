import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { clearAuth, readUser, STORAGE_KEYS } from "@/lib/authStorage";
import { AuthService } from "@/services/auth";
import type { AuthenticatedUser } from "@/types/auth";

interface AuthValue {
  user: AuthenticatedUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}

const Context = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(readUser);
  const [loading, setLoading] = useState(Boolean(readUser()));

  useEffect(() => {
    if (!loading) return;
    AuthService.me()
      .then((current) => {
        setUser(current);
        localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(current));
      })
      .catch(() => {
        clearAuth();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [loading]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await AuthService.login(username, password);
    localStorage.setItem(STORAGE_KEYS.accessToken, response.access_token);
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(response.user));
    setUser(response.user);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  const hasPermission = useCallback(
    (permission: string) =>
      Boolean(
        user?.is_super_admin ||
          user?.permissions?.includes("*:*") ||
          user?.permissions?.includes(permission),
      ),
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, logout, hasPermission }),
    [user, loading, login, logout, hasPermission],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(Context);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
