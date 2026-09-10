import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { clearAuth, readUser, saveAuth, saveUser, STORAGE_KEYS } from "@/lib/authStorage";
import { AuthService } from "@/services/auth";
import type { AuthenticatedUser, LoginResponse } from "@/types/auth";

interface AuthValue {
  user: AuthenticatedUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginAsAdmin: () => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}

const Context = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(readUser);
  const [loading, setLoading] = useState(Boolean(readUser()));
  const generation = useRef(0);

  useEffect(() => () => { generation.current += 1; }, []);

  useEffect(() => {
    if (!loading) return;
    let active = true;
    const requestGeneration = generation.current;
    const isCurrent = () => active && requestGeneration === generation.current;
    AuthService.me()
      .then((current) => {
        if (!isCurrent()) return;
        saveUser(current);
        setUser(current);
      })
      .catch(() => {
        if (isCurrent() && !localStorage.getItem(STORAGE_KEYS.accessToken)) setUser(null);
      })
      .finally(() => { if (isCurrent()) setLoading(false); });
    return () => { active = false; };
  }, [loading]);

  const signIn = useCallback(async (request: () => Promise<LoginResponse>) => {
    const requestGeneration = ++generation.current;
    const response = await request();
    if (requestGeneration !== generation.current) return;
    saveAuth(response);
    setUser(response.user);
    setLoading(false);
  }, []);

  const login = useCallback((username: string, password: string) =>
    signIn(() => AuthService.login(username, password)), [signIn]);

  const loginAsAdmin = useCallback(() => signIn(() => AuthService.loginAsAdmin()), [signIn]);

  const logout = useCallback(() => {
    generation.current += 1;
    clearAuth();
    setUser(null);
    setLoading(false);
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
    () => ({ user, loading, login, loginAsAdmin, logout, hasPermission }),
    [user, loading, login, loginAsAdmin, logout, hasPermission],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(Context);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
