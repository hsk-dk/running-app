import { createContext, useContext } from "react";

/** Who is using the app: a child gets a simpler app, and a parent (admin) can set that up. */
export type MeInfo = { isChild: boolean; isAdmin: boolean; id: number | null };

export const MeContext = createContext<MeInfo>({ isChild: false, isAdmin: false, id: null });
export const useMe = (): MeInfo => useContext(MeContext);
