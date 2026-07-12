import catalog from "@shared/strategy_catalog.json";
import type { Strategy } from "../types";

export const strategies = catalog as Strategy[];
export const strategyById = (id?: string) => strategies.find((strategy) => strategy.id === id);
