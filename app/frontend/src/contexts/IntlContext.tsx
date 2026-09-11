import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
type Locale = "tr" | "en";
type Catalogue = Record<string, string>;
const loaders: Record<Locale, () => Promise<{ default: Catalogue }>> = {
  tr: () => import("@/locales/tr.json"),
  en: () => import("@/locales/en.json"),
};

interface IntlValue {
  locale: string;
  setLocale: (value: string) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
}

const Context = createContext<IntlValue | null>(null);

export function IntlProvider({ children }: { children: ReactNode }) {
  const [locale, selectLocale] = useState<Locale>("tr");
  const [loaded, setLoaded] = useState<{ locale: Locale; messages: Catalogue } | null>(null);
  useEffect(() => {
    let active = true;
    void loaders[locale]().then(({ default: messages }) => {
      if (active) { document.documentElement.lang = locale; setLoaded({ locale, messages }); }
    });
    return () => { active = false; };
  }, [locale]);
  const value = useMemo(
    () => ({
      locale: loaded?.locale ?? locale,
      setLocale: (next: string) => selectLocale(next === "en" ? "en" : "tr"),
      t: (key: string, values?: Record<string, string | number>) => {
        const message = loaded?.messages[key];
        if (message === undefined && import.meta.env.DEV && loaded) throw new Error(`Missing locale key: ${key}`);
        return (message ?? key).replace(/\{(\w+)\}/g, (placeholder, name: string) =>
          values && Object.hasOwn(values, name) ? String(values[name]) : placeholder);
      },
    }),
    [locale, loaded],
  );
  if (!loaded) return null;
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useIntl(): IntlValue {
  const value = useContext(Context);
  if (!value) throw new Error("useIntl must be used inside IntlProvider");
  return value;
}
