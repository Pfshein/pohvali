import { useEffect, useState } from "react";

import type { MascotCollection, PurchaseOutcome } from "../lib/mascots-api";
import { Collection } from "./Collection";

interface CollectionPanelProps {
  load: () => Promise<MascotCollection>;
  purchase: (code: string) => Promise<PurchaseOutcome>;
  activate: (code: string) => Promise<void>;
}

type Phase = "loading" | "ready" | "error";

export function CollectionPanel({ load, purchase, activate }: CollectionPanelProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [collection, setCollection] = useState<MascotCollection | null>(null);
  const [busyCode, setBusyCode] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  async function refresh() {
    try {
      setCollection(await load());
      setPhase("ready");
    } catch {
      setPhase("error");
    }
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await load();
        if (active) {
          setCollection(data);
          setPhase("ready");
        }
      } catch {
        if (active) setPhase("error");
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function run(code: string, action: () => Promise<void>, done: string) {
    if (busyCode) return;
    setBusyCode(code);
    setMessage("");
    try {
      await action();
      await refresh();
      setMessage(done);
    } catch {
      setMessage("Не получилось. Можно попробовать ещё раз.");
    } finally {
      setBusyCode(null);
      window.setTimeout(() => setMessage(""), 2600);
    }
  }

  if (phase === "loading") {
    return (
      <section className="collection" aria-busy="true">
        <p className="collection__note">Открываем коллекцию…</p>
      </section>
    );
  }

  if (phase === "error" || collection === null) {
    return (
      <section className="collection">
        <p className="collection__note">Не удалось открыть коллекцию.</p>
        <button className="secondary-button" onClick={() => void refresh()}>
          Попробовать снова
        </button>
      </section>
    );
  }

  return (
    <>
      <Collection
        mascots={collection.mascots}
        balance={collection.balance}
        busyCode={busyCode}
        onPurchase={(code) =>
          void run(code, async () => void (await purchase(code)), "Спутник теперь с тобой ⭐")
        }
        onActivate={(code) => void run(code, () => activate(code), "Теперь он рядом")}
      />
      {message && <div className="toast" role="status">{message}</div>}
    </>
  );
}
