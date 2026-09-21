import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { Organization, Session, User, authApi } from "@/features/auth/api";
import { setUnauthorizedHandler, tokenStore } from "@/shared/api/client";

interface AuthState {
  user: User | null;
  organization: Organization | null;
  /** Vrai tant qu'on n'a pas déterminé si une session existe. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (payload: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => void;
  /** Après modification du profil de l'agence, sans refaire un tour complet. */
  setOrganization: (organization: Organization) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  const apply = useCallback((session: Session) => {
    tokenStore.set(session.access_token);
    setUser(session.user);
    setOrganization(session.organization);
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setOrganization(null);
  }, []);

  // Un 401 sur n'importe quel appel ramène immédiatement à l'écran de connexion,
  // plutôt que de laisser une interface vide se remplir d'erreurs.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // Restauration de session au chargement : le jeton survit au rafraîchissement.
  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(({ user: u, organization: o }) => {
        setUser(u);
        setOrganization(o);
      })
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      organization,
      loading,
      login: async (email, password) => apply(await authApi.login({ email, password })),
      signup: async (payload) => apply(await authApi.signup(payload)),
      logout,
      setOrganization,
    }),
    [user, organization, loading, apply, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans un AuthProvider");
  return context;
}
