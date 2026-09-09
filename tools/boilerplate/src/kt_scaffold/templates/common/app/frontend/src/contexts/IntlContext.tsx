import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import en from "@/locales/en.json";
import tr from "@/locales/tr.json";

type MessageTree = { [key: string]: string | MessageTree };
const catalogues: Record<string, MessageTree> = { en, tr };

function lookup(catalogue: MessageTree, key: string): string | undefined {
  const direct = catalogue[key];
  if (typeof direct === "string") return direct;
  let current: string | MessageTree | undefined = catalogue;
  for (const part of key.split(".")) {
    if (typeof current === "string" || current === undefined) return undefined;
    const entry: [string, string | MessageTree] | undefined = Object.entries(
      current,
    ).find(([candidate]) => candidate === part);
    if (entry === undefined) return undefined;
    current = entry[1];
  }
  return typeof current === "string" ? current : undefined;
}

interface IntlValue {
  locale: string;
  setLocale: (value: string) => void;
  t: (key: string) => string;
}

const Context = createContext<IntlValue | null>(null);

export function IntlProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState("en");
  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t: (key: string) =>
        lookup(catalogues[locale] ?? catalogues.en, key) ??
        lookup(catalogues.en, key) ??
        key,
    }),
    [locale],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useIntl(): IntlValue {
  const value = useContext(Context);
  if (!value) throw new Error("useIntl must be used inside IntlProvider");
  return value;
}
