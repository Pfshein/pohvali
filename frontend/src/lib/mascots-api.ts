import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export type MascotStateName = "owned" | "affordable" | "locked";

export interface MascotItem {
  code: string;
  name: string;
  blurb: string;
  assetPath: string;
  starter: boolean;
  price: number | null;
  state: MascotStateName;
  unlocked: boolean;
  active: boolean;
}

export interface MascotCollection {
  balance: number;
  activeMascot: string | null;
  mascots: MascotItem[];
}

export interface PurchaseOutcome {
  code: string;
  balance: number;
  newlyPurchased: boolean;
}

function isMascotState(value: unknown): value is MascotStateName {
  return value === "owned" || value === "affordable" || value === "locked";
}

function isMascotItem(value: unknown): value is {
  code: string;
  name: string;
  blurb: string;
  asset_path: string;
  starter: boolean;
  price: number | null;
  state: MascotStateName;
  unlocked: boolean;
  active: boolean;
} {
  return (
    typeof value === "object"
    && value !== null
    && "code" in value && typeof value.code === "string"
    && "name" in value && typeof value.name === "string"
    && "blurb" in value && typeof value.blurb === "string"
    && "asset_path" in value && typeof value.asset_path === "string"
    && "starter" in value && typeof value.starter === "boolean"
    && "price" in value && (typeof value.price === "number" || value.price === null)
    && "state" in value && isMascotState(value.state)
    && "unlocked" in value && typeof value.unlocked === "boolean"
    && "active" in value && typeof value.active === "boolean"
  );
}

export async function loadCollection(
  client: TelegramClient,
  fetcher: Fetcher = fetch,
): Promise<MascotCollection> {
  const initData = await client.getInitData();

  const response = await fetcher("/api/v1/mascots", {
    method: "GET",
    headers: { Authorization: `tma ${initData}` },
  });

  if (!response.ok) throw new Error("Could not load the collection");

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object"
    || payload === null
    || !("balance" in payload)
    || typeof payload.balance !== "number"
    || !("active_mascot" in payload)
    || !(typeof payload.active_mascot === "string" || payload.active_mascot === null)
    || !("mascots" in payload)
    || !Array.isArray(payload.mascots)
    || !payload.mascots.every(isMascotItem)
  ) {
    throw new Error("Could not load the collection");
  }

  return {
    balance: payload.balance,
    activeMascot: payload.active_mascot,
    mascots: payload.mascots.map((item) => ({
      code: item.code,
      name: item.name,
      blurb: item.blurb,
      assetPath: item.asset_path,
      starter: item.starter,
      price: item.price,
      state: item.state,
      unlocked: item.unlocked,
      active: item.active,
    })),
  };
}

export async function purchaseMascot(
  client: TelegramClient,
  code: string,
  fetcher: Fetcher = fetch,
): Promise<PurchaseOutcome> {
  const initData = await client.getInitData();

  const response = await fetcher(`/api/v1/mascots/${encodeURIComponent(code)}/purchase`, {
    method: "POST",
    headers: { Authorization: `tma ${initData}` },
  });

  if (!response.ok) throw new Error("Could not open this companion");

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object"
    || payload === null
    || !("code" in payload)
    || typeof payload.code !== "string"
    || !("balance" in payload)
    || typeof payload.balance !== "number"
    || !("newly_purchased" in payload)
    || typeof payload.newly_purchased !== "boolean"
  ) {
    throw new Error("Could not open this companion");
  }

  return {
    code: payload.code,
    balance: payload.balance,
    newlyPurchased: payload.newly_purchased,
  };
}

export async function activateMascot(
  client: TelegramClient,
  code: string,
  fetcher: Fetcher = fetch,
): Promise<void> {
  const initData = await client.getInitData();

  const response = await fetcher(`/api/v1/mascots/${encodeURIComponent(code)}/active`, {
    method: "PUT",
    headers: { Authorization: `tma ${initData}` },
  });

  if (!response.ok) throw new Error("Could not choose this companion");
}
